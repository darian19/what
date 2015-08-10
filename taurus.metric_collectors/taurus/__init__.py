# See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
try:
    __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
    from pkgutil import extend_path
    __path__ = extend_path(__path__, __name__)

# NOTE: as a namespace package, this __init__.py MUST NOT contain anything else
# besides the namespace package boilerplate
# `__import__("pkg_resources").declare_namespace(__name__)`

