def get_memory_store():
    from .chroma_store import get_memory_store as _fn
    return _fn()

class ChromaMemoryStore:
    def __new__(cls, *args, **kwargs):
        from .chroma_store import ChromaMemoryStore as _CMS
        return _CMS(*args, **kwargs)
