"""
性别感知系统全链路自动化测试 / Automated Test Suite for Gender-Aware Translation System
测试项包含：
1. 用户性别数据库持久化与手动指令 (User Gender DB & Manual Setting)
2. AI 多模态画像自动推断 (AI Multimodal Inference from Name/Avatar)
3. 动态敬语注入翻译输出验证 (Gendered Translation Verification: ครับ/ค่ะ, ผม/ฉัน)
4. 指令集完备性检查 (Command Matching Sets)
"""
import os
import sys
import unittest

# 将项目根目录加入 sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import user_manager
import translator
from main import MALE_COMMANDS, FEMALE_COMMANDS, RESET_COMMANDS, QUERY_COMMANDS


class TestUserGenderDB(unittest.TestCase):
    """测试用户性别本地 SQLite 存储、查询、手动更新与重置"""

    def setUp(self):
        self.test_user_id = "test_user_line_unittest_123"
        user_manager.reset_user_gender(self.test_user_id)

    def tearDown(self):
        user_manager.reset_user_gender(self.test_user_id)

    def test_default_gender_is_neutral(self):
        gender, set_by = user_manager.get_user_gender(self.test_user_id)
        self.assertEqual(gender, "neutral")
        self.assertEqual(set_by, "default")

    def test_manual_set_male(self):
        user_manager.set_user_gender_manual(self.test_user_id, "male", display_name="Test Male")
        gender, set_by = user_manager.get_user_gender(self.test_user_id)
        self.assertEqual(gender, "male")
        self.assertEqual(set_by, "manual")

    def test_manual_set_female(self):
        user_manager.set_user_gender_manual(self.test_user_id, "female", display_name="Test Female")
        gender, set_by = user_manager.get_user_gender(self.test_user_id)
        self.assertEqual(gender, "female")
        self.assertEqual(set_by, "manual")

    def test_reset_gender(self):
        user_manager.set_user_gender_manual(self.test_user_id, "male")
        user_manager.reset_user_gender(self.test_user_id)
        gender, set_by = user_manager.get_user_gender(self.test_user_id)
        self.assertEqual(gender, "neutral")
        self.assertEqual(set_by, "default")

    def test_manual_overrides_ai(self):
        # 手动设置后，AI 推断不得覆盖 manual 记录
        user_manager.set_user_gender_manual(self.test_user_id, "female")
        inferred = user_manager.infer_and_save_gender(
            self.test_user_id, display_name="Somchai Mr Male"
        )
        self.assertEqual(inferred, "female")
        gender, set_by = user_manager.get_user_gender(self.test_user_id)
        self.assertEqual(gender, "female")
        self.assertEqual(set_by, "manual")


class TestCommandMatching(unittest.TestCase):
    """测试性别指令集匹配"""

    def test_male_commands(self):
        for cmd in ['我是男生', '我是男', '我是男的', '/male', 'ผมเป็นผู้ชาย', '/gender male']:
            self.assertIn(cmd.lower(), MALE_COMMANDS)

    def test_female_commands(self):
        for cmd in ['我是女生', '我是女', '我是女的', '/female', 'ฉันเป็นผู้หญิง', 'ดิฉันเป็นผู้หญิง', '/gender female']:
            self.assertIn(cmd.lower(), FEMALE_COMMANDS)

    def test_reset_commands(self):
        for cmd in ['重置性别', '清除性别', '/gender reset', 'รีเซ็ตเพศ']:
            self.assertIn(cmd.lower(), RESET_COMMANDS)

    def test_query_commands(self):
        for cmd in ['我的性别', '/gender', 'เพศของฉัน']:
            self.assertIn(cmd.lower(), QUERY_COMMANDS)


class TestGenderTranslations(unittest.TestCase):
    """测试不同性别下的泰语敬语与人称代词翻译质量"""

    test_sentence = "非常感谢，我现在通知工厂"

    def test_male_translation(self):
        translated = translator.translate_message(self.test_sentence, gender="male")
        self.assertIsNotNone(translated)
        print(f"\n[Test Male Result]:\n{translated}")
        # 男性敬语必须包含 ครับ，第一人称代词通常使用 ผม
        self.assertIn("ครับ", translated)
        self.assertIn("ผม", translated)
        # 绝不能出现女性敬语 ค่ะ/คะ 或斜杠双选 ครับ/ค่ะ
        self.assertNotIn("ค่ะ", translated)
        self.assertNotIn("คะ", translated)
        self.assertNotIn("ครับ/ค่ะ", translated)
        self.assertNotIn("ผม/ฉัน", translated)

    def test_female_translation(self):
        translated = translator.translate_message(self.test_sentence, gender="female")
        self.assertIsNotNone(translated)
        print(f"\n[Test Female Result]:\n{translated}")
        # 女性敬语必须包含 ค่ะ 或 คะ，代词使用 ฉัน 或 ดิฉัน
        has_female_particle = ("ค่ะ" in translated or "คะ" in translated)
        has_female_pronoun = ("ฉัน" in translated or "ดิฉัน" in translated)
        self.assertTrue(has_female_particle, "Female translation should contain ค่ะ or คะ")
        self.assertTrue(has_female_pronoun, "Female translation should contain ฉัน or ดิฉัน")
        # 绝不能出现男性敬语 ครับ 或斜杠双选
        self.assertNotIn("ครับ", translated)
        self.assertNotIn("ครับ/ค่ะ", translated)
        self.assertNotIn("ผม/ฉัน", translated)

    def test_neutral_translation(self):
        translated = translator.translate_message(self.test_sentence, gender="neutral")
        self.assertIsNotNone(translated)
        print(f"\n[Test Neutral Result]:\n{translated}")
        # 中性商务翻译不应包含斜杠双选
        self.assertNotIn("ครับ/ค่ะ", translated)
        self.assertNotIn("ผม/ฉัน", translated)
        self.assertNotIn("/ค่ะ", translated)
        self.assertNotIn("/ฉัน", translated)


class TestAIProfileInference(unittest.TestCase):
    """测试通过昵称的 AI 自动推断功能"""

    def setUp(self):
        self.ai_test_user = "test_ai_user_999"
        user_manager.reset_user_gender(self.ai_test_user)

    def tearDown(self):
        user_manager.reset_user_gender(self.ai_test_user)

    def test_infer_male_name(self):
        gender = user_manager.infer_and_save_gender(
            self.ai_test_user, display_name="John (Mr. Smith)"
        )
        print(f"\n[AI Infer Male]: {gender}")
        self.assertEqual(gender, "male")

    def test_infer_female_name(self):
        gender = user_manager.infer_and_save_gender(
            self.ai_test_user, display_name="Anna (Ms. Taylor)"
        )
        print(f"\n[AI Infer Female]: {gender}")
        self.assertEqual(gender, "female")


if __name__ == "__main__":
    unittest.main()
