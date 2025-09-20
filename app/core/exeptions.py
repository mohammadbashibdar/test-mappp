from fastapi import Request
from fastapi.responses import JSONResponse

# Exception اختصاصی
class CustomAppException(Exception):
    def __init__(self, message: str, status_code: int = 400, data=None):
        self.message = message
        self.status_code = status_code
        self.data = data

#Exception Handler مخصوص FastAPI
async def custom_exception_handler(request: Request, exc: CustomAppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "data": exc.data
        },
    )
