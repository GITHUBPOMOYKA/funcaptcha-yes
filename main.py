import base64
import hashlib
import json
import os
import time
from io import BytesIO

from PIL import Image
from fastapi import FastAPI, Request
from funcaptcha_challenger import predict, model
from pydantic import BaseModel

from util.log import logger
from util.model_support_fetcher import ModelSupportFetcher

app = FastAPI()
PORT = 8181
IS_DEBUG = True
fetcher = ModelSupportFetcher()
question_file_path = "question/questions.json"


class Task(BaseModel):
    type: str
    image: str
    question: str


class TaskData(BaseModel):
    clientKey: str
    task: Task
    softID: str = 'default_value'


def process_image(base64_image: str, variant: str):
    if base64_image.startswith("data:image/"):
        base64_image = base64_image.split(",")[1]

    image_bytes = base64.b64decode(base64_image)
    image = Image.open(BytesIO(image_bytes))

    ans = predict(image, variant)
    logger.debug(f"predict {variant} result: {ans}")
    return ans


def create_task_response(taskId: str, question: str, image: str):
    ans = {
        "errorId": 0,
        "errorCode": "",
        "status": "ready",
        "solution": {
            "label": "arrows_objecthand",
            "taskId": taskId,
            "objects": [process_image(image, '3d_rollball_objects')]
        }
    }

    # 把question写入本地
    os.makedirs('question', exist_ok=True)
    questions = {}
    if os.path.exists(question_file_path) and os.path.getsize(question_file_path) > 0:
        with open(question_file_path, "r") as f:
            questions = json.load(f)
    if question not in questions:
        questions[question] = True
        with open(question_file_path, "w") as f:
            json.dump(questions, f)
    return ans


@app.post("/createTask")
async def create_task(request: Request):
    try:
        request_data = await request.json()
        data = TaskData.parse_obj(request_data)
        taskId = hashlib.md5(str(int(time.time() * 1000)).encode()).hexdigest()
        return create_task_response(taskId, data.task.question, data.task.image)
    except Exception as e:
        logger.error(f"error: {e}")
        return {
            "errorId": 1,
            "errorCode": "ERROR_UNKNOWN",
            "status": "error",
            "solution": {"objects": []}
        }


@app.get("/support")
async def support():
    # 从文件中读取模型列表
    return fetcher.supported_models
@app.get("/question")
async def question():
    # 读取问题列表
    try:
        questions = {}
        if os.path.exists(question_file_path) and os.path.getsize(question_file_path) > 0:
            with open(question_file_path, "r") as f:
                questions = json.load(f)
        return questions
    except Exception as e:
        return {}



@app.post("/getBalance")
async def balance(request: Request):
    # 从文件中读取模型列表
    return {
        "softBalance": 0,
        "inviteBalance": 0,
        "inviteBy": "99",
        "errorId": 0,
        "balance": 9999999
    }


if __name__ == "__main__":
    import uvicorn

    # 设置模型自动更新为False
    model.auto_update = False
    uvicorn.run(app, host="0.0.0.0", port=PORT)