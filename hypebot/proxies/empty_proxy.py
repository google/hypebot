# Lint as: python3
"""A fake proxy for use in testing where external request should not be made."""

from hypebot.proxies import proxy_lib


class EmptyProxy(proxy_lib.Proxy):
  """Proxy that always returns an empty response."""

  def _GetUrl(self, url, params, headers=None):
    return None
