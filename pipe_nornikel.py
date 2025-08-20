from openai import OpenAI
import boto3
import os
import random
from pydantic import BaseModel
from typing import Optional, Union
from enum import Enum

import hashlib
from tqdm import tqdm
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
WINDOW_SIZE = 50000


client = OpenAI(base_url="http://localhost:8555/v1", api_key="EMPTY")

class InstructPair(BaseModel):
    """Модель для пары задание-ответ"""
    task: str
    answer: str

class QuestionPair(BaseModel):
    """Модель для пары задание-ответ"""
    question: str
    answer: str

class Decision(str, Enum):
    """Enum для решения проверки"""
    YES = "да"
    NO = "нет"

class CheckResult(BaseModel):
    """Модель для результата проверки"""
    decision: Decision

def get_responce(prompt_template_path: str, text=None, question=None, answer=None, use_structured_output=False, response_model=None) -> Union[str, BaseModel, None]:
    with open(prompt_template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Подставляем текст в шаблон
    prompt = template.format(text=text, question=question, answer=answer)

    if use_structured_output and response_model:
        response = client.beta.chat.completions.parse(
            model="Qwen/Qwen3-14b",
            messages=[
                {"role": "system", "content": ""},
                {"role": "user", "content": prompt}
            ],
            response_format=response_model,
            temperature=0.7,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        
        return response.choices[0].message.parsed
    else:
        response = client.chat.completions.create(
            model="Qwen/Qwen3-14b",
            messages=[
                {"role": "system", "content": ""},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )

        print(response.choices[0].message.content)
        return response.choices[0].message.content


def get_instruct_pair(file_text: str) -> tuple[Optional[str], Optional[str]]:
    """Извлекает пары инструкций из файла"""
    try:
        num = 0 #random.randint(0, max(0, len(file_text)-WINDOW_SIZE))
        
        # Получаем structured output для пары задание-ответ
        result = get_responce(
            "prompts/instruct_choose_snippet.txt", 
            text=file_text[num:num+WINDOW_SIZE],
            use_structured_output=True,
            response_model=InstructPair
        )
        
        if result and isinstance(result, InstructPair):
            # Проверяем качество пары с помощью structured output
            check_result = get_responce(
                "prompts/instruct_check.txt", 
                text=file_text[num:num+WINDOW_SIZE], 
                question=result.task, 
                answer=result.answer,
                use_structured_output=True,
                response_model=CheckResult
            )
            
            if check_result and isinstance(check_result, CheckResult) and check_result.decision == Decision.YES:
                return result.task, result.answer
        
        return None, None
    except Exception as e:
        print(f"Ошибка при обработке текста: {e}")
        return None, None


def get_question_pair(file_text: str) -> tuple[Optional[str], Optional[str]]:
    """Извлекает пары вопрос-ответ из файла"""
    try:
        num = 0 #random.randint(0, max(0, len(file_text)-WINDOW_SIZE))
        
        # Получаем structured output для пары вопрос-ответ
        result = get_responce(
            "prompts/qa_choose_snippet.txt", 
            text=file_text[num:num+WINDOW_SIZE],
            use_structured_output=True,
            response_model=QuestionPair
        )
        
        if result and isinstance(result, QuestionPair):
            # Проверяем качество пары с помощью structured output
            check_result = get_responce(
                "prompts/qa_check.txt", 
                text=file_text[num:num+WINDOW_SIZE], 
                question=result.question, 
                answer=result.answer,
                use_structured_output=True,
                response_model=CheckResult
            )
            
            if check_result and isinstance(check_result, CheckResult) and check_result.decision == Decision.YES:
                return result.question, result.answer
        
        return None, None
    except Exception as e:
        print(f"Ошибка при обработке текста: {e}")
        return None, None


if __name__ == "__main__":
    # Настройка S3 клиента
    s3_client = boto3.client(
        's3',
        endpoint_url=os.getenv('S3_ENDPOINT_URL'),
        aws_access_key_id=os.getenv('S3_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('S3_SECRET_ACCESS_KEY'),
        region_name='ru-central1'  # Yandex Cloud region
    )
    
    bucket_name = 'crawler-data'
    articles_prefix = 'articles/'
    
    while True:
        try:
            # Получаем список всех объектов в папке articles
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=articles_prefix
            )
            
            if 'Contents' in response:
                for obj in tqdm(response['Contents']):
                    file_key = obj['Key']
                    
                    # Проверяем, что это текстовый файл (не папка и имеет расширение .txt)
                    if not file_key.endswith('/') and file_key.endswith('.txt'):
                        print(f"Обрабатываем файл: {file_key}")
                        
                        # Создаем короткое имя файла используя хеш
                        file_hash = hashlib.md5(file_key.encode()).hexdigest()[:10]
                        local_file_path = f"/tmp/article_{file_hash}.txt"
                        s3_client.download_file(bucket_name, file_key, local_file_path)
                        with open(local_file_path, "r", encoding='utf-8') as file:
                            data = file.read()
                        
                        try:
                        # Выполняем функцию get_instruct_pairs для файла

                            for i in range(10):
                                instruction, answer = get_instruct_pair(data)
                                if instruction is not None and answer is not None:
                                    with open(f"instruct_pairs.txt", "a", encoding='utf-8') as file:
                                        file.write(instruction + "\n" + answer + "\n=======\n")
                                
                                # Генерируем пары вопрос-ответ
                                question, qa_answer = get_question_pair(data)
                                if question is not None and qa_answer is not None:
                                    with open(f"qa_pairs.txt", "a", encoding='utf-8') as file:
                                        file.write(question + "\n" + qa_answer + "\n=======\n")
                                    
                            # print(f"Найдено {len(instruct_pairs)} пар инструкций в файле {file_key}")
                                
                        except Exception as e:
                            print(f"Ошибка при обработке файла {file_key}: {e}")
                        
                        finally:
                            # Удаляем временный файл
                            if os.path.exists(local_file_path):
                                os.remove(local_file_path)
            else:
                print("В папке articles не найдено файлов")
                
        except Exception as e:
            print(f"Ошибка при работе с S3: {e}")