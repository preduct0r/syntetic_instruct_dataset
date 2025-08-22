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
from transformers import AutoTokenizer

model_id = "Qwen/Qwen3-235B-A22B-Instruct-2507-FP8"  # your exact model id
tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True)

# Загружаем переменные окружения
load_dotenv()
WINDOW_SIZE = 25000

# Глобальная переменная для подсчета токенов
all_tokens = 0

token = os.getenv("YANDEX_API_KEY")
folder_id = os.getenv("YANDEX_FOLDER_ID")
class InstructPair(BaseModel):
    """Модель для пары задание-ответ"""
    task: str
    answer: str

class MultipleInstructPairs(BaseModel):
    """Модель для множественных пар задание-ответ"""
    pairs: list[InstructPair]

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

class CriterionCheck(BaseModel):
    """Модель для проверки одного критерия"""
    criterion_number: int
    decision: Decision
    reasoning: str

class DetailedCheckResult(BaseModel):
    """Модель для детального результата проверки"""
    criterion_1: CriterionCheck
    criterion_2: CriterionCheck
    criterion_3: CriterionCheck
    criterion_4: CriterionCheck
    criterion_5: CriterionCheck
    criterion_6: CriterionCheck
    criterion_7: CriterionCheck
    criterion_8: CriterionCheck
    overall_decision: Decision
    overall_reasoning: str

def get_local_responce(prompt_template_path: str, text=None, question=None, answer=None, use_structured_output=False, response_model=None) -> Union[str, BaseModel, None]:
    with open(prompt_template_path, "r", encoding="utf-8") as f:
        template = f.read()
    client = OpenAI(base_url="http://localhost:8555/v1", api_key="EMPTY")
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
        raise ValueError("use_structured_output и response_model должны быть True и не None соответственно")
    

def get_qwen235_responce(prompt_template_path: str, text=None, question=None, answer=None, use_structured_output=False, response_model=None) -> Union[str, BaseModel, None]:
    global all_tokens

    client = OpenAI(base_url="https://llm.api.cloud.yandex.net/v1", api_key=token)
    with open(prompt_template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Подставляем текст в шаблон
    prompt = template.format(text=text, question=question, answer=answer)
    
    # Подсчитываем входные токены
    input_tokens = len(tokenizer.encode(prompt))

    if use_structured_output and response_model:
        response = client.chat.completions.parse(
            model=f"gpt://{folder_id}/qwen3-235b-a22b-fp8/latest",
            messages=[
                {"role": "developer", "content": ""},
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            response_format=response_model,
            temperature=0.7,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        
        # Подсчитываем выходные токены
        response_content = response.choices[0].message.content
        output_tokens = len(tokenizer.encode(response_content)) if response_content else 0
        total_tokens = input_tokens + output_tokens

        all_tokens += total_tokens
        print(f"Сожжено токенов: {all_tokens}")
        
        return response.choices[0].message.parsed
    else:
        raise ValueError("use_structured_output и response_model должны быть True и не None соответственно")


def get_instruct_pair(file_text: str) -> list[tuple[str, str]]:
    """Извлекает множественные пары инструкций из файла"""
    try:
        # Получаем structured output для множественных пар задание-ответ
        result = get_qwen235_responce(
            "prompts/instruct_choose_snippet.txt", 
            text=file_text[:WINDOW_SIZE],
            use_structured_output=True,
            response_model=MultipleInstructPairs
        )
        
        validated_pairs = []
        
        if result and isinstance(result, MultipleInstructPairs):
            for pair in result.pairs:
                # Проверяем качество каждой пары с помощью structured output
                check_result = get_local_responce(
                    "prompts/instruct_check_detailed.txt", 
                    text=file_text[:WINDOW_SIZE], 
                    question=pair.task, 
                    answer=pair.answer,
                    use_structured_output=True,
                    response_model=DetailedCheckResult
                )
                
                if check_result and isinstance(check_result, DetailedCheckResult) and check_result.overall_decision == Decision.YES:
                    validated_pairs.append((pair.task, pair.answer))
        
        return validated_pairs
    except Exception as e:
        print(f"Ошибка при обработке текста: {e}")
        return []


# def get_question_pair(file_text: str) -> tuple[Optional[str], Optional[str]]:
#     """Извлекает пары вопрос-ответ из файла"""
#     try:
#         # Получаем structured output для пары вопрос-ответ
#         result = get_responce(
#             "prompts/qa_choose_snippet.txt", 
#             text=file_text[:WINDOW_SIZE],
#             use_structured_output=True,
#             response_model=QuestionPair
#         )
        
#         if result and isinstance(result, QuestionPair):
#             # Проверяем качество пары с помощью structured output
#             check_result = get_responce(
#                 "prompts/qa_check.txt", 
#                 text=file_text[:WINDOW_SIZE], 
#                 question=result.question, 
#                 answer=result.answer,
#                 use_structured_output=True,
#                 response_model=CheckResult
#             )
            
#             if check_result and isinstance(check_result, CheckResult) and check_result.decision == Decision.YES:
#                 return result.question, result.answer
        
#         return None, None
#     except Exception as e:
#         print(f"Ошибка при обработке текста: {e}")
#         return None, None


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
            # Используем пагинацию для получения всех объектов в папке articles
            paginator = s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=bucket_name,
                Prefix=articles_prefix
            )
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in tqdm(page['Contents'], desc="Processing files"):
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
                                instruction_pairs = get_instruct_pair(data)
                                for instruction, answer in instruction_pairs:
                                    with open(f"instruct_pairs.txt", "a", encoding='utf-8') as file:
                                        file.write(instruction + "\n" + answer + "\n=======\n")
                                
                                # # Генерируем пары вопрос-ответ
                                # question, qa_answer = get_question_pair(data)
                                # if question is not None and qa_answer is not None:
                                #     with open(f"qa_pairs.txt", "a", encoding='utf-8') as file2:
                                #         file2.write(question + "\n" + qa_answer + "\n=======\n")
                                        
                                # print(f"Найдено {len(instruct_pairs)} пар инструкций в файле {file_key}")
                                    
                            except Exception as e:
                                print(f"Ошибка при обработке файла {file_key}: {e}")
                            
                            finally:
                                # Удаляем временный файл
                                if os.path.exists(local_file_path):
                                    os.remove(local_file_path)
                else:
                    print("В текущей странице не найдено файлов")
            
            print("Обработка всех файлов завершена")
            break  # Выходим из while True после обработки всех файлов
                
        except Exception as e:
            print(f"Ошибка при работе с S3: {e}")
            break  # Выходим из цикла при ошибке