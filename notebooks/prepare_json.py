#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path

def parse_instruct_pairs(file_path):
    """
    Парсит файл instruct_pairs и возвращает список словарей
    формата {"instruction": str, "answer": str}
    
    Args:
        file_path (str): Путь к файлу instruct_pairs
        
    Returns:
        list: Список словарей с парами instruction/answer
    """
    pairs = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Разделяем на блоки по "======="
        blocks = content.split('=======')
        
        for block in blocks:
            block = block.strip()
            if not block:
                continue
                
            # Разделяем на instruction и answer по "===="
            if '====' in block:
                parts = block.split('====')
                if len(parts) >= 2:
                    instruction = parts[0].strip()
                    answer = parts[1].strip()
                    
                    if instruction and answer:
                        pairs.append({
                            "instruction": instruction,
                            "answer": answer
                        })
                        
    except FileNotFoundError:
        print(f"Файл {file_path} не найден!")
        return []
    except Exception as e:
        print(f"Ошибка при чтении файла {file_path}: {e}")
        return []
    
    return pairs

def save_to_json(data, output_file):
    """
    Сохраняет данные в JSON файл
    
    Args:
        data (list): Список словарей для сохранения
        output_file (str): Путь к выходному JSON файлу
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Данные успешно сохранены в {output_file}")
    except Exception as e:
        print(f"Ошибка при сохранении в {output_file}: {e}")

def main():
    """
    Основная функция для обработки всех файлов instruct_pairs
    """
    # Определяем рабочую директорию
    script_dir = Path(__file__).parent.parent
    
    # Файлы для обработки
    input_files = [
        script_dir / "instruct_pairs.txt",
        script_dir / "instruct_pairs_v1.txt",
        script_dir / "instruct_pairsv0.txt"
    ]
    
    all_pairs = []
    
    # Обрабатываем каждый файл
    for file_path in input_files:
        if file_path.exists():
            print(f"Обрабатываем файл: {file_path}")
            pairs = parse_instruct_pairs(file_path)
            print(f"Найдено пар в {file_path.name}: {len(pairs)}")
            all_pairs.extend(pairs)
        else:
            print(f"Файл {file_path} не существует, пропускаем...")
    
    # Удаляем дубликаты (если есть)
    unique_pairs = []
    seen = set()
    
    for pair in all_pairs:
        # Создаем хэш для проверки уникальности
        pair_hash = hash((pair["instruction"], pair["answer"]))
        if pair_hash not in seen:
            seen.add(pair_hash)
            unique_pairs.append(pair)
    
    print(f"\nВсего найдено пар: {len(all_pairs)}")
    print(f"Уникальных пар: {len(unique_pairs)}")
    
    if unique_pairs:
        # Сохраняем в JSON файл
        output_file = script_dir / "instruct_dataset.json"
        save_to_json(unique_pairs, output_file)
        
        # Выводим количество строк в получившемся файле
        with open(output_file, 'r', encoding='utf-8') as f:
            line_count = sum(1 for line in f)
        
        print("\n" + "="*60)
        print("📊 РЕЗУЛЬТАТЫ ОБРАБОТКИ:")
        print("="*60)
        print(f"📄 Файл создан: {output_file}")
        print(f"📝 Количество строк в JSON файле: {line_count}")
        print(f"📋 Количество записей в датасете: {len(unique_pairs)}")
        print("="*60)
        
        # Показываем пример первой записи
        if unique_pairs:
            print(f"\n💡 Пример первой записи:")
            print(json.dumps(unique_pairs[0], ensure_ascii=False, indent=2))
    else:
        print("Не найдено ни одной валидной пары instruction/answer")

if __name__ == "__main__":
    main()
