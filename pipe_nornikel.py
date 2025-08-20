from openai import OpenAI
import boto3
import os
import hashlib
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

client = OpenAI(base_url="http://localhost:8555/v1", api_key="EMPTY")

response = client.chat.completions.create(
    model="Qwen/Qwen3-14b",
    messages=[
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ],
    temperature=0.7,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)

print(response.choices[0].message.content)


def get_instruct_pairs(file_path: str) -> list[tuple[str, str]]:
    """Извлекает пары инструкций из файла"""
    with open(file_path, "r", encoding='utf-8') as file:
        data = file.read()
    
    # Здесь должна быть логика парсинга файла для извлечения пар инструкций
    # Пока возвращаем пустой список
    return []


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
    
    try:
        # Получаем список всех объектов в папке articles
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=articles_prefix
        )
        
        if 'Contents' in response:
            for obj in response['Contents']:
                file_key = obj['Key']
                
                # Проверяем, что это текстовый файл (не папка и имеет расширение .txt)
                if not file_key.endswith('/') and file_key.endswith('.txt'):
                    print(f"Обрабатываем файл: {file_key}")
                    
                    # Создаем короткое имя файла используя хеш
                    file_hash = hashlib.md5(file_key.encode()).hexdigest()[:10]
                    local_file_path = f"/tmp/article_{file_hash}.txt"
                    s3_client.download_file(bucket_name, file_key, local_file_path)
                    
                    try:
                        # Выполняем функцию get_instruct_pairs для файла
                        instruct_pairs = get_instruct_pairs(local_file_path)
                        print(f"Найдено {len(instruct_pairs)} пар инструкций в файле {file_key}")
                        
                        # Здесь можно добавить дополнительную обработку результатов
                        for i, (instruction, response) in enumerate(instruct_pairs):
                            print(f"  Пара {i+1}: {instruction[:50]}... -> {response[:50]}...")
                            
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