import json
import time
from typing import Optional, List

import requests
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog

from cereal import custom


class ModelParser:
  """Handles parsing of model data into cereal objects"""

  @staticmethod
  def _parse_model(full_name: str, file_name: str, uri_data: dict, model_type: custom.ModelManagerSP.Type) -> custom.ModelManagerSP.Model:
    model = custom.ModelManagerSP.Model()
    download_uri = custom.ModelManagerSP.DownloadUri()

    download_uri.uri = uri_data["url"]
    download_uri.sha256 = uri_data["sha256"]

    model.fullName = full_name
    model.fileName = file_name
    model.downloadUri = download_uri
    model.type = model_type

    return model

  @staticmethod
  def _parse_bundle(key: str, value: dict) -> custom.ModelManagerSP.ModelBundle:
    model_bundle = custom.ModelManagerSP.ModelBundle()
    models = []

    # Parse main driving model
    models.append(ModelParser._parse_model(
      value["full_name"],
      value["file_name"],
      value["download_uri"],
      custom.ModelManagerSP.Type.drive
    ))

    # Parse navigation model if exists
    if value.get("download_uri_nav"):
      models.append(ModelParser._parse_model(
        value["full_name_nav"],
        value["file_name_nav"],
        value["download_uri_nav"],
        custom.ModelManagerSP.Type.navigation
      ))

    # Parse metadata model if exists
    if value.get("download_uri_metadata"):
      models.append(ModelParser._parse_model(
        value["full_name_metadata"],
        value["file_name_metadata"],
        value["download_uri_metadata"],
        custom.ModelManagerSP.Type.metadata
      ))

    model_bundle.index = int(value["index"])
    model_bundle.internalName = key
    model_bundle.displayName = value["display_name"]
    model_bundle.models = models
    model_bundle.status = 0

    return model_bundle

  @staticmethod
  def parse_models(json_data: dict) -> List[custom.ModelManagerSP.ModelBundle]:
    return [ModelParser._parse_bundle(key, value) for key, value in json_data.items()]


class ModelCache:
  """Handles caching of model data to avoid frequent remote fetches"""

  def __init__(self, params: Params, cache_timeout: int = int(3600 * 1e9)):
    self.params = params
    self.cache_timeout = cache_timeout
    self._LAST_SYNC_KEY = "ModelManager_LastSyncTime"
    self._CACHE_KEY = "ModelManager_ModelsCache"

  def _is_expired(self) -> bool:
    """Checks if the cache has expired"""
    current_time = int(time.monotonic() * 1e9)
    last_sync = int(self.params.get(self._LAST_SYNC_KEY, encoding="utf-8") or 0)
    return (current_time - last_sync) >= self.cache_timeout

  def get(self) -> tuple[Optional[dict], bool]:
    """
    Retrieves cached model data and expiration status atomically.
    Returns: Tuple of (cached_data, is_expired)
    """
    cached_data = self.params.get(self._CACHE_KEY, encoding="utf-8")
    if not cached_data:
      return None, True

    try:
      return json.loads(cached_data), self._is_expired()
    except json.JSONDecodeError:
      cloudlog.warning("Failed to parse cached models data")
      return None, True

  def set(self, data: dict) -> None:
    """Updates the cache with new model data"""
    self.params.put(self._CACHE_KEY, json.dumps(data))
    self.params.put(self._LAST_SYNC_KEY, str(int(time.monotonic() * 1e9)))


class ModelFetcher:
  """Handles fetching and caching of model data from remote source"""
  MODEL_URL = "https://docs.sunnypilot.ai/models_v5.json"

  def __init__(self, params: Params):
    self.model_cache = ModelCache(params)
    self.model_parser = ModelParser()

  def _fetch_and_cache_models(self) -> List[custom.ModelManagerSP.ModelBundle]:
    """Fetches fresh model data from remote and updates cache"""
    try:
      response = requests.get(self.MODEL_URL, timeout=10)
      response.raise_for_status()
      json_data = response.json()

      self.model_cache.set(json_data)
      cloudlog.debug("Successfully updated models cache")
      return self.model_parser.parse_models(json_data)
    except Exception:
      cloudlog.exception(f"Error fetching models")
      raise

  def get_available_models(self) -> List[custom.ModelManagerSP.ModelBundle]:
    """Gets the list of available models, with smart cache handling"""
    cached_data, is_expired = self.model_cache.get()

    # If we have valid cache data, use it
    if cached_data and not is_expired:
      cloudlog.debug("Using valid cached models data")
      return self.model_parser.parse_models(cached_data)

    # Cache is expired or empty, try to fetch fresh data
    if is_expired:
      try:
        return self._fetch_and_cache_models()
      except Exception:
        if cached_data:
          cloudlog.warning("Failed to fetch fresh data. Using expired cache as fallback")
          return self.model_parser.parse_models(cached_data)
        cloudlog.exception("Failed to fetch fresh data and no cache available")
        raise  # Only raise if we have no fallback
