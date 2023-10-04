from typing import Any


class fake:
    def __init__(self) -> None:
        pass

    def get(self, name, index):
        return self.__dict__[name]


class BlobIndex:
    def __getattribute__(self, __name: str) -> Any:
        return self.__dict__[__name]

    def __setattr__(self, __name: str, __value: Any) -> None:
        pass

    def __getitem__(self, key):
        return BlobIndex(self, key)


class Blob:

    def __getattribute__(self, __name: str) -> Any:
        return self.__dict__[__name]

    def __setattr__(self, __name: str, __value: Any) -> None:
        pass

    def __getitem__(self, key):
        return 3
    
    def __class_getitem__(self, key):
        return 4


blob = Blob
blob.fred = 1

print(blob.fred)
print(blob[1])