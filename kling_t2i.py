import torch
import requests
import time
import jwt
import numpy as np
import random
from PIL import Image
from io import BytesIO
import traceback
from datetime import datetime

class KlingT2I:
    def __init__(self):
        self.base_url = "https://api.klingai.com/v1"
        self.create_endpoint = "/images/generations"
        self.query_endpoint = "/images/generations"
        self.min_poll_interval = 5
        self.max_attempts = 30  # 25分钟超时

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_name": (["kling-v1", "kling-v1-5"], {"default": "kling-v1-5"}),  # 新增模型选择
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "aspect_ratio": (["16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3", "21:9"], {"default": "1:1"}),
                "batch_size": ("INT", {"min": 1, "max": 9, "default": 1}),
                "access_key": ("STRING", {"default": ""}),
                "secret_key": ("STRING", {"password": True}),
                "seed": ("INT", {"min": 0, "max": 999999999, "default": 0}),
            },
            "optional": {
                "image_fidelity": ("FLOAT", {"min": 0.0, "max": 1.0, "default": 0.5}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "generate"
    CATEGORY = "KlingAI"

    def _generate_jwt(self, ak: str, sk: str) -> str:
        return jwt.encode(
            payload={
                "iss": ak.strip(),
                "exp": int(time.time()) + 1800,
                "nbf": int(time.time()) - 5
            },
            key=sk.strip(),
            algorithm="HS256",
            headers={"kid": "v1"}
        )

    def _validate_response(self, response: requests.Response) -> dict:
        data = response.json()
        if response.status_code != 200 or data.get("code") != 0:
            error_msg = data.get("message", f"HTTP {response.status_code} 错误")
            raise ConnectionError(error_msg)
        return data

    def _poll_task(self, headers: dict, task_id: str) -> dict:
        poll_url = f"{self.base_url}{self.query_endpoint}/{task_id}"
        start_time = time.time()
        
        current_interval = self.min_poll_interval
        last_status = None
        
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = requests.get(poll_url, headers=headers, timeout=15)
                data = self._validate_response(response)
                task_data = data["data"]
                
                if task_data["task_status"] != last_status:
                    print(f"[状态变更] {task_data['task_status']} (耗时: {int(time.time()-start_time)}秒)")
                    last_status = task_data["task_status"]
                
                if last_status == "succeed":
                    return task_data
                if last_status == "failed":
                    raise RuntimeError(task_data.get("task_status_msg", "任务失败"))
                
                current_interval = min(current_interval * 1.3, 60)
                time.sleep(current_interval)
            
            except requests.exceptions.RequestException as e:
                print(f"[网络重试] 尝试 {attempt}/{self.max_attempts}")
                time.sleep(current_interval)

        raise TimeoutError("处理超时")

    def generate(self, model_name, prompt, negative_prompt, aspect_ratio, 
                batch_size, access_key, secret_key, seed, image_fidelity=0.5):
        try:
            # 密钥验证
            if not (access_key.strip() and secret_key.strip()):
                raise ValueError("API密钥不可为空")
            
            # 构建请求
            headers = {
                "Authorization": f"Bearer {self._generate_jwt(access_key, secret_key)}",
                "Content-Type": "application/json"
            }
            payload = {
                "model_name": model_name,  # 使用选择的模型版本
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "aspect_ratio": aspect_ratio,
                "n": batch_size,
                "strength": image_fidelity,
                "seed": seed if seed !=0 else random.randint(1,999999999)
            }

            # 提交任务
            resp = requests.post(
                f"{self.base_url}{self.create_endpoint}",
                headers=headers,
                json=payload,
                timeout=30
            )
            task_id = self._validate_response(resp)["data"]["task_id"]
            print(f"[任务ID] {task_id} | 模型: {model_name}")

            # 获取结果
            result = self._poll_task(headers, task_id)
            
            # 严格数量验证
            generated_images = result["task_result"]["images"]
            if len(generated_images) != batch_size:
                raise RuntimeError(f"生成数量异常（预期：{batch_size}，实际：{len(generated_images)}）")

            # 图片处理
            images = []
            for img in generated_images:
                response = requests.get(img["url"], timeout=30)
                image = Image.open(BytesIO(response.content)).convert("RGB")
                image_np = np.array(image).astype(np.float32) / 255.0
                images.append(torch.from_numpy(image_np)[None,])
            
            return (torch.cat(images, dim=0), )

        except Exception as e:
            print(f"[致命错误] {str(e)}")
            raise

NODE_CLASS_MAPPINGS = {"Kling_v1_5_T2I": KlingT2I}
NODE_DISPLAY_NAME_MAPPINGS = {"Kling_v1_5_T2I": "🔥 Kling Text2Image"}
