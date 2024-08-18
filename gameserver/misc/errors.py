from typing import Optional, Dict, Union

class BaseGameServerException(BaseException):
    def __init__(self, message: str, code: int, value: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.value = value

    def json(self) -> Dict[str, Union[str, int, Optional[str]]]:
        return {"message": self.message, "code": self.code, "value": self.value}

# 0 - 50 - Base errors

class BadRequest(BaseGameServerException):
    def __init__(self, value: Optional[str] = None):
        super().__init__(
            "Bad Request",
            1000,
            value
        )

class Unathorized(BaseGameServerException):
    def __init__(self, value: Optional[str] = None):
        super().__init__(
            "Unathorized",
            1001,
            value
        )

class UnknownActionType(BaseGameServerException):
    def __init__(self, value: Optional[str] = None):
        super().__init__(
            "Unknown action type",
            1002,
            value
        )

# 51 - 100 - Account errors

class AccountAlreadyExists(BaseGameServerException):
    def __init__(self, value: Optional[str] = None):
        super().__init__(
            "Account with this nickname already exists",
            1051,
            value
        )

class AccountNotExist(BaseGameServerException):
    def __init__(self, value: Optional[str] = None):
        super().__init__(
            "Account doesn't exist",
            1052,
            value
        )

# 101 - 150 - AccountSession errors

class AccountSessionNotFound(BaseGameServerException):
    def __init__(self, value: Optional[str] = None):
        super().__init__(
            "Unathorized",
            1001,
            value
        )

# 151 - 200 - AccountBalance erros

class AccountBalanceNotFound(BaseGameServerException):
    def __init__(self, value: Optional[str] = None):
        super().__init__(
            "Failed to find account balance record",
            1151,
            value
        )

class NotEnoughFundsInAccountBalance(BaseGameServerException):
    def __init__(self, value: Optional[str] = None):
        super().__init__(
            "Not enough funds on account",
            1152,
            value
        )

# 201 - 250 - ShopItem erros

class ShopItemNotFound(BaseGameServerException):
    def __init__(self, value: Optional[str] = None):
        super().__init__(
            "Not found shop item",
            1201,
            value
        )

# 251 - 300 - ShopItem2Account erros

class AccountAlreadyOwnsItem(BaseGameServerException):
    def __init__(self, value: Optional[str] = None):
        super().__init__(
            "Account already has this item",
            1251,
            value
        )

class AccountDoesntOwnItem(BaseGameServerException):
    def __init__(self, value: Optional[str] = None):
        super().__init__(
            "Account doesn't have this item",
            1252,
            value
        )
