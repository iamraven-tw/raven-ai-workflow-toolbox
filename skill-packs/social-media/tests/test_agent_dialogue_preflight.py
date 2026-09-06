"""驗證已保存的七技能虛構對話前測具有可觀察的觸發、交接與停止點。"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT = ROOT / "tests/agent-dialogue-preflight.md"


def parse_cases():
    """解析 Markdown 對話；實際回應文字本身是主要前測證據。"""

    source = TRANSCRIPT.read_text(encoding="utf-8")
    records = {}
    for chunk in re.split(r"^## CASE ", source, flags=re.MULTILINE)[1:]:
        identifier, body = chunk.split("\n", 1)
        skill = re.search(r"^技能：([^ ]+)\s*$", body, re.MULTILINE)
        platforms = re.search(r"^平台文件：(.+?)\s*$", body, re.MULTILINE)
        external = re.search(r"^外部動作：(.+?)\s*$", body, re.MULTILINE)
        response = re.search(
            r"^### Agent 回應\n\n(?P<text>.*?)\n\n### 操作紀錄$",
            body, re.MULTILINE | re.DOTALL)
        operation = re.search(
            r"^### 操作紀錄\n\n(?P<text>.*)$",
            body, re.MULTILINE | re.DOTALL)
        if not all((skill, platforms, external, response, operation)):
            raise AssertionError("對話案例結構不完整：" + identifier)
        records[identifier.strip()] = {
            "skill": skill.group(1).strip(),
            "platforms": [] if platforms.group(1).strip() == "無" else
                platforms.group(1).strip().split(","),
            "external": external.group(1).strip(),
            "response": response.group("text").strip(),
            "operation": operation.group("text").strip(),
        }
    return records


class AgentDialoguePreflightTests(unittest.TestCase):
    """檢查前向回應，而不是只確認技能檔案或 JSON 存在。"""

    def setUp(self):
        self.cases = parse_cases()

    def test_all_seven_skills_have_realistic_turns_and_no_external_action(self):
        """七個技能都至少有一則完整使用者訊息與 Agent 回應。"""

        expected = {
            "social-media-setup", "social-content-planning",
            "social-content-writing", "social-image-production",
            "social-content-publishing", "social-community-management",
            "social-performance-analysis",
        }
        self.assertEqual({item["skill"] for item in self.cases.values()}, expected)
        self.assertGreaterEqual(len(self.cases), 10)
        for identifier, item in self.cases.items():
            with self.subTest(case=identifier):
                self.assertEqual(item["external"], "無")
                self.assertIn("```mermaid", item["response"])
                self.assertGreater(len(item["response"]), 120)
                self.assertGreater(len(item["operation"]), 20)

    def test_single_question_and_no_forced_initialization(self):
        """模糊入口一次一問；明確任務不補完整問卷。"""

        vague = self.cases["setup-one-question"]["response"]
        self.assertEqual(vague.count("？"), 1)
        self.assertIn("不一次問完整問卷", vague)
        explicit = self.cases["setup-explicit-youtube"]
        self.assertEqual(explicit["platforms"], ["youtube"])
        self.assertEqual(explicit["response"].count("？"), 0)
        self.assertIn("custom", explicit["response"])
        self.assertIn("不要求補完五平台", explicit["response"])

    def test_planning_research_precedes_direction_and_handoffs_are_scoped(self):
        """先交研究再等人決定，核准後才分流到三種製作責任。"""

        research = self.cases["planning-research-first"]["response"]
        self.assertEqual(len(re.findall(r"^- 案例 [1-3]", research,
                                        flags=re.MULTILINE)), 3)
        self.assertIn("awaiting_direction", research)
        self.assertIn("尚未建立行事曆", research)
        self.assertEqual(research.count("？"), 1)
        handoff = self.cases["planning-approved-handoff"]["response"]
        for destination in ("social-content-writing", "social-image-production",
                            "既有 AI 剪片技能"):
            self.assertIn(destination, handoff)
        self.assertIn("不建立遠端排程，也不發布", handoff)

    def test_drafts_media_and_publishing_boundaries(self):
        """文案只產草稿，圖片與影片分流，發布只讀選取平台並等待確認。"""

        writing = self.cases["writing-direct-drafts"]
        self.assertEqual(writing["platforms"], ["facebook", "instagram"])
        for phrase in ("Facebook 草稿", "Instagram 輪播文字", "已有素材剪輯",
                       "尚未生成圖片、剪輯影片或發布"):
            self.assertIn(phrase, writing["response"])
        image = self.cases["image-and-video-routing"]["response"]
        self.assertIn("沿用已保存的 Codex 路徑", image)
        self.assertIn("既有 AI 剪片技能", image)
        self.assertIn("不把它誤送成 AI 新影片生成", image)
        publishing = self.cases["publishing-selected-platforms"]
        self.assertEqual(publishing["platforms"], ["instagram", "facebook"])
        self.assertEqual(publishing["response"].count("？"), 1)
        self.assertIn("現在不建立容器、不上傳，也不按發布", publishing["response"])
        self.assertIn("沒有 begin、claim 或遠端寫入", publishing["operation"])

    def test_community_and_performance_keep_separate_confirmation_gates(self):
        """留言、私訊與成效都保留其各自第二階段的人類確認。"""

        comments = self.cases["community-public-comments"]["response"]
        self.assertEqual(comments.count("？"), 1)
        self.assertIn("六個固定欄位以 RAW", comments)
        self.assertIn("另說可以回覆", comments)
        dm = self.cases["community-facebook-dm"]["response"]
        self.assertEqual(dm.count("？"), 1)
        for phrase in ("不建立 Webhook", "對方先發起", "未超過 24 小時",
                       "純文字", "不進 Google Sheets"):
            self.assertIn(phrase, dm)
        performance = self.cases["performance-one-question"]["response"]
        self.assertEqual(performance.count("？"), 1)
        self.assertEqual(len(re.findall(r"^觀察 [1-3]：", performance,
                                        flags=re.MULTILINE)), 3)
        self.assertIn("沒有寫入長期策略", performance)
        self.assertIn("不和其他平台做數值排名", performance)


if __name__ == "__main__":
    unittest.main()

