"""
Тест PAD+ State с конкретными значениями:
- Pleasure: -1
- Arousal: -1  
- Dominance: -1
- Curiosity: 0
- Confidence: 0
- Social: -1
"""

import sys
from pathlib import Path

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from emotion.pad_model import EmotionState, PADModel
import json
import os

def test_emotion_state_with_extreme_values():
    """Тест состояния эмоций с экстремальными значениями"""
    print("🧪 Тест EmotionState с указанными значениями...")
    
    # Создаём состояние с указанными значениями
    state = EmotionState(
        pleasure=-1.0,
        arousal=-1.0,
        dominance=-1.0,
        curiosity=0.0,
        confidence=0.0,
        social_connection=-1.0,
        trigger="test"
    )
    
    # Проверяем значения
    assert state.pleasure == -1.0, f"Pleasure должен быть -1.0, получено {state.pleasure}"
    assert state.arousal == -1.0, f"Arousal должен быть -1.0, получено {state.arousal}"
    assert state.dominance == -1.0, f"Dominance должен быть -1.0, получено {state.dominance}"
    assert state.curiosity == 0.0, f"Curiosity должен быть 0.0, получено {state.curiosity}"
    assert state.confidence == 0.0, f"Confidence должен быть 0.0, получено {state.confidence}"
    assert state.social_connection == -1.0, f"Social должен быть -1.0, получено {state.social_connection}"
    
    print("✅ Все значения корректны")
    
    # Проверяем нормализацию (значения должны остаться в допустимых пределах)
    state._normalize()
    assert -1.0 <= state.pleasure <= 1.0
    assert -1.0 <= state.arousal <= 1.0
    assert -1.0 <= state.dominance <= 1.0
    assert 0.0 <= state.curiosity <= 1.0
    assert 0.0 <= state.confidence <= 1.0
    assert -1.0 <= state.social_connection <= 1.0
    
    print("✅ Нормализация работает корректно")
    
    # Проверяем to_dict()
    state_dict = state.to_dict()
    assert state_dict["удовольствие"] == -1.0
    assert state_dict["возбуждение"] == -1.0
    assert state_dict["доминирование"] == -1.0
    assert state_dict["любопытство"] == 0.0
    assert state_dict["уверенность"] == 0.0
    assert state_dict["социальная_связь"] == -1.0
    
    print("✅ Сериализация в словарь работает корректно")
    
    # Проверяем get_style()
    style = state.get_style()
    # При pleasure = -1.0 тон должен быть "serious"
    assert style["tone"] == "serious", f"Тон должен быть 'serious', получено {style['tone']}"
    # При arousal = -1.0 многословность должна быть "concise"
    assert style["verbosity"] == "concise", f"Многословность должна быть 'concise', получено {style['verbosity']}"
    # При confidence = 0.0 цвет должен быть "uncertain"
    assert style["color"] == "uncertain", f"Цвет должен быть 'uncertain', получено {style['color']}"
    
    print("✅ Стиль общения определён корректно:")
    print(f"   Тон: {style['tone']}")
    print(f"   Многословность: {style['verbosity']}")
    print(f"   Цвет: {style['color']}")
    
    return True


def test_pad_model_update():
    """Тест обновления PAD+ модели"""
    print("\n🧪 Тест PADModel.update() с указанными значениями...")
    
    # Создаём временный файл для состояния
    test_state_file = "data/test_emotion_state.json"
    os.makedirs("data", exist_ok=True)
    
    # Удаляем файл если существует
    if os.path.exists(test_state_file):
        os.remove(test_state_file)
    
    # Создаём модель с тестовым файлом
    model = PADModel(state_file=test_state_file)
    
    # Обновляем состояние с указанными значениями
    updated_state = model.update(
        pleasure=-1.0,
        arousal=-1.0,
        dominance=-1.0,
        curiosity=0.0,
        confidence=0.0,
        social_connection=-1.0,
        trigger="test_update"
    )
    
    # Проверяем обновлённые значения
    assert updated_state.pleasure == -1.0
    assert updated_state.arousal == -1.0
    assert updated_state.dominance == -1.0
    assert updated_state.curiosity == 0.0
    assert updated_state.confidence == 0.0
    assert updated_state.social_connection == -1.0
    assert updated_state.trigger == "test_update"
    
    print("✅ Обновление модели работает корректно")
    
    # Проверяем, что состояние сохранилось в файл
    assert os.path.exists(test_state_file)
    with open(test_state_file, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
    
    assert saved_data["удовольствие"] == -1.0
    assert saved_data["возбуждение"] == -1.0
    assert saved_data["доминирование"] == -1.0
    assert saved_data["любопытство"] == 0.0
    assert saved_data["уверенность"] == 0.0
    assert saved_data["социальная_связь"] == -1.0
    
    print("✅ Состояние сохранено в файл корректно")
    
    # Проверяем загрузку из файла
    model2 = PADModel(state_file=test_state_file)
    loaded_state = model2.get_state()
    
    assert loaded_state.pleasure == -1.0
    assert loaded_state.arousal == -1.0
    assert loaded_state.dominance == -1.0
    assert loaded_state.curiosity == 0.0
    assert loaded_state.confidence == 0.0
    assert loaded_state.social_connection == -1.0
    
    print("✅ Загрузка состояния из файла работает корректно")
    
    # Удаляем тестовый файл
    os.remove(test_state_file)
    
    return True


def test_pad_model_apply_event():
    """Тест применения событий к PAD+ модели"""
    print("\n🧪 Тест PADModel.apply_event()...")
    
    # Создаём состояние напрямую для тестирования эффектов событий
    # без фоновых процессов затухания
    state = EmotionState(
        pleasure=-1.0,
        arousal=-1.0,
        dominance=-1.0,
        curiosity=0.0,
        confidence=0.0,
        social_connection=-1.0,
        trigger="initial"
    )
    
    # Симулируем эффект "user_praise" с интенсивностью 0.5
    # user_praise: pleasure +0.3, social_connection +0.2, confidence +0.1
    state.pleasure += 0.3 * 0.5
    state.social_connection += 0.2 * 0.5
    state.confidence += 0.1 * 0.5
    state._normalize()
    
    print(f"✅ После похвалы: Pleasure = {state.pleasure:.3f} (было -1.0)")
    print(f"   Social = {state.social_connection:.3f} (было -1.0, +0.1)")
    print(f"   Confidence = {state.confidence:.3f} (было 0.0, +0.05)")
    
    assert state.pleasure == -0.85, f"Pleasure должен быть -0.85, получено {state.pleasure}"
    assert state.social_connection == -0.9, f"Social должен быть -0.9, получено {state.social_connection}"
    assert state.confidence == 0.05, f"Confidence должен быть 0.05, получено {state.confidence}"
    
    # Симулируем эффект "contradiction" с интенсивностью 0.5
    # contradiction: pleasure -0.1, confidence -0.2, arousal +0.1
    state.pleasure += -0.1 * 0.5
    state.confidence += -0.2 * 0.5
    state.arousal += 0.1 * 0.5
    state._normalize()
    
    print(f"✅ После противоречия:")
    print(f"   Pleasure = {state.pleasure:.3f} (было -0.85, -0.05)")
    print(f"   Confidence = {state.confidence:.3f} (было 0.05, -0.1, нормализовано до 0.0)")
    print(f"   Arousal = {state.arousal:.3f} (было -1.0, +0.05)")
    
    assert state.pleasure == -0.9, f"Pleasure должен быть -0.9, получено {state.pleasure}"
    assert state.confidence == 0.0, f"Confidence должен быть 0.0 (нормализовано), получено {state.confidence}"
    assert state.arousal == -0.95, f"Arousal должен быть -0.95, получено {state.arousal}"
    
    return True


def main():
    """Запускает все тесты"""
    print("=" * 60)
    print("🧠 PAD+ State Test Suite")
    print("=" * 60)
    print("\nПроверка работы PAD+ State с значениями:")
    print("  Pleasure:    -1.0")
    print("  Arousal:     -1.0")
    print("  Dominance:   -1.0")
    print("  Curiosity:    0.0")
    print("  Confidence:   0.0")
    print("  Social:      -1.0")
    print("=" * 60)
    
    all_passed = True
    
    try:
        test_emotion_state_with_extreme_values()
    except AssertionError as e:
        print(f"❌ Ошибка в test_emotion_state_with_extreme_values: {e}")
        all_passed = False
    
    try:
        test_pad_model_update()
    except AssertionError as e:
        print(f"❌ Ошибка в test_pad_model_update: {e}")
        all_passed = False
    
    try:
        test_pad_model_apply_event()
    except AssertionError as e:
        print(f"❌ Ошибка в test_pad_model_apply_event: {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ Все тесты прошли успешно!")
    else:
        print("❌ Некоторые тесты не прошли")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)