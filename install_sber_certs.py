#!/usr/bin/env python3
"""
Скрипт для установки SSL сертификатов Сбера для GigaChat
"""

import os
import sys
import ssl
import subprocess
import tempfile
from pathlib import Path

def get_cert_from_server():
    """Получить сертификат с сервера Сбера"""
    print("🔍 Получение сертификата с ngw.devices.sberbank.ru:9443...")
    
    try:
        # Используем OpenSSL для получения сертификата
        cmd = [
            "openssl", "s_client", "-connect", "ngw.devices.sberbank.ru:9443",
            "-showcerts", "-servername", "ngw.devices.sberbank.ru"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"⚠️  OpenSSL ошибка: {result.stderr[:200]}")
            return None
        
        # Извлекаем сертификаты из вывода
        certs = []
        lines = result.stdout.split('\n')
        current_cert = []
        in_cert = False
        
        for line in lines:
            if 'BEGIN CERTIFICATE' in line:
                in_cert = True
                current_cert = [line]
            elif 'END CERTIFICATE' in line:
                current_cert.append(line)
                certs.append('\n'.join(current_cert))
                in_cert = False
            elif in_cert:
                current_cert.append(line)
        
        print(f"✅ Найдено {len(certs)} сертификатов")
        return certs
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def install_to_windows_cert_store(cert_path):
    """Установить сертификат в хранилище Windows"""
    print(f"🔧 Установка сертификата из {cert_path}...")
    
    try:
        # Используем certutil для установки
        cmd = [
            "certutil",
            "-addstore",
            "-f",
            "Root",  # Доверенные корневые центры
            str(cert_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Сертификат установлен в доверенные корневые центры")
            return True
        else:
            print(f"⚠️  Certutil ошибка: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка установки: {e}")
        return False

def install_to_python_certifi(cert_content):
    """Добавить сертификат в certifi"""
    print("🔧 Добавление сертификата в Python certifi...")
    
    try:
        import certifi
        
        cacert_path = certifi.where()
        print(f"📁 Certifi путь: {cacert_path}")
        
        # Читаем текущее содержимое
        with open(cacert_path, 'r', encoding='utf-8') as f:
            existing = f.read()
        
        # Проверяем, не добавлен ли уже
        if 'Sber CA' in existing or 'sber' in existing.lower():
            print("ℹ️  Сертификат Сбера уже добавлен в certifi")
            return True
        
        # Добавляем сертификат
        with open(cacert_path, 'a', encoding='utf-8') as f:
            f.write('\n\n# Sber CA Certificates for GigaChat\n')
            f.write(cert_content)
        
        print("✅ Сертификат добавлен в certifi")
        return True
        
    except ImportError:
        print("⚠️  certifi не установлен. Установите: pip install certifi")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    print("=" * 60)
    print("Установка SSL сертификатов Сбера для GigaChat")
    print("=" * 60)
    
    # Проверяем наличие OpenSSL
    try:
        subprocess.run(["openssl", "version"], capture_output=True, check=True)
        print("✅ OpenSSL найден")
    except:
        print("❌ OpenSSL не найден. Установите OpenSSL или используйте ручную установку.")
        print("\nИнструкция:")
        print("1. Скачайте с https://slproweb.com/products/Win32OpenSSL.html")
        print("2. Установите Win64 OpenSSL")
        print("3. Добавьте в PATH")
        sys.exit(1)
    
    # Получаем сертификаты
    certs = get_cert_from_server()
    
    if not certs:
        print("\n⚠️  Не удалось получить сертификаты автоматически.")
        print("Используйте ручную установку:")
        print("  Документация: docs/GIGACHAT_SSL_SETUP.md")
        sys.exit(1)
    
    # Сохраняем во временные файлы
    temp_dir = tempfile.mkdtemp()
    cert_files = []
    
    for i, cert in enumerate(certs):
        cert_path = Path(temp_dir) / f"sber_cert_{i}.pem"
        with open(cert_path, 'w') as f:
            f.write(cert)
        cert_files.append(cert_path)
        print(f"💾 Сохранен: {cert_path}")
    
    # Устанавливаем первый (корневой) сертификат
    if cert_files:
        print("\n📋 Установка в Windows...")
        install_to_windows_cert_store(cert_files[-1])  # Последний = корневой
        
        print("\n📋 Установка в Python certifi...")
        with open(cert_files[-1], 'r') as f:
            install_to_python_certifi(f.read())
    
    # Очистка
    for f in cert_files:
        try:
            f.unlink()
        except:
            pass
    try:
        Path(temp_dir).rmdir()
    except:
        pass
    
    print("\n" + "=" * 60)
    print("Готово!")
    print("=" * 60)
    print("\n⚠️  ВАЖНО: Верните verify=True в llm_service.py:")
    print("  c:\\пад ал датабаз а  чистый\\PAD+ AI чистый\\backend\\runtime\\llm_service.py")
    print("  (строки 557, 582, 658, 687)")
    print("\n🔄 Перезапустите backend после изменений")

if __name__ == "__main__":
    main()
    input("\nНажмите Enter для выхода...")
