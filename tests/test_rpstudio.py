"""RoleplayStudio 单元测试。

运行：``python -m unittest discover -s tests -v``
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from rpstudio.core import (
    Character,
    Event,
    Project,
    Relationship,
    Store,
    StudioError,
    validate,
)
from rpstudio.render import context_pack, full_bible


def adult(name: str, age: int = 28, cid: str | None = None) -> Character:
    return Character(id=cid or name.lower(), name=name, age=age)


class TempMixin(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = Path(tempfile.mkdtemp(prefix="rpstudio-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self._dir, ignore_errors=True)


class TestAgeGate(unittest.TestCase):
    """「明确成年角色」是硬约束，必须在数据层拦住。"""

    def test_rejects_minor(self):
        project = Project()
        with self.assertRaises(StudioError) as ctx:
            project.add_character(adult("小夏", 17))
        self.assertIn("成年人", str(ctx.exception))

    def test_accepts_adult_boundary(self):
        project = Project()
        project.add_character(adult("林夏", 18))
        self.assertEqual(project.characters[0].age, 18)

    def test_rejects_duplicate_name(self):
        project = Project()
        project.add_character(adult("林夏", 29))
        with self.assertRaises(StudioError):
            project.add_character(adult("林夏", 30, cid="other"))


class TestRelationships(unittest.TestCase):
    def setUp(self):
        self.project = Project()
        self.project.add_character(adult("林夏", 29, "linxia"))
        self.project.add_character(adult("周砚", 32, "zhouyan"))

    def test_symmetric_key(self):
        self.assertEqual(Relationship.key("a", "b"), Relationship.key("b", "a"))

    def test_upsert_same_pair(self):
        self.project.set_relationship(Relationship("linxia", "zhouyan", "暧昧", 2))
        self.project.set_relationship(Relationship("zhouyan", "linxia", "交往", 3))
        self.assertEqual(len(self.project.relationships), 1)
        self.assertEqual(self.project.relationship_of("linxia", "zhouyan").stage, "交往")

    def test_intimacy_bounds(self):
        with self.assertRaises(StudioError):
            self.project.set_relationship(Relationship("linxia", "zhouyan", "暧昧", 9))

    def test_unknown_endpoint(self):
        with self.assertRaises(StudioError):
            self.project.set_relationship(Relationship("linxia", "ghost", "暧昧", 1))


class TestTimeline(unittest.TestCase):
    def setUp(self):
        self.project = Project()
        self.project.add_character(adult("林夏", 29, "linxia"))
        self.project.add_character(adult("周砚", 32, "zhouyan"))

    def test_auto_seq_increments(self):
        first = self.project.add_event(Event(0, "初遇", ["linxia"], "躲雨"))
        second = self.project.add_event(Event(0, "第二次", ["linxia"], "留书"))
        self.assertEqual((first.seq, second.seq), (1, 2))

    def test_recent_events_filtered_by_participant(self):
        self.project.add_character(adult("第三人", 30, "third"))
        self.project.add_event(Event(0, "A", ["linxia"], ""))
        self.project.add_event(Event(0, "B", ["third"], ""))
        self.project.add_event(Event(0, "C", ["linxia", "zhouyan"], ""))
        recent = self.project.recent_events(5, participants=["linxia"])
        self.assertEqual([event.title for event in recent], ["A", "C"])

    def test_unknown_participant(self):
        with self.assertRaises(StudioError):
            self.project.add_event(Event(0, "X", ["ghost"], ""))


class TestRender(unittest.TestCase):
    def setUp(self):
        self.project = Project(title="雨夜书店", premise="两个成年人反复偶遇", tone="克制")
        self.project.add_character(
            Character(
                id="linxia",
                name="林夏",
                age=29,
                role="常客",
                speech_style="短句",
                boundaries=["不写非自愿情节"],
                preferences=["慢节奏"],
            )
        )
        self.project.add_character(adult("周砚", 32, "zhouyan"))
        self.project.set_relationship(Relationship("linxia", "zhouyan", "暧昧", 2, history=["递毛巾"]))
        self.project.add_event(Event(0, "递毛巾", ["linxia", "zhouyan"], "他递了条干毛巾"))

    def test_pack_states_adults(self):
        text = context_pack(self.project)
        self.assertIn("成年人", text)
        self.assertIn("林夏(29岁)", text)
        self.assertIn("周砚(32岁)", text)

    def test_pack_includes_relationship_and_event(self):
        text = context_pack(self.project, focus=["林夏", "周砚"])
        self.assertIn("暧昧", text)
        self.assertIn("亲密度：2/5", text)
        self.assertIn("递毛巾", text)

    def test_pack_includes_boundaries(self):
        text = context_pack(self.project)
        self.assertIn("共同边界", text)
        self.assertIn("不写非自愿情节", text)

    def test_focus_limits_characters(self):
        text = context_pack(self.project, focus=["林夏"])
        self.assertIn("林夏", text)
        self.assertNotIn("周砚(32岁)", text)

    def test_bible_is_superset(self):
        # 造 3 条事件：圣经应全含，"最近 1 条"只含最后一条
        self.project.add_event(Event(0, "第二次", ["linxia"], "留书"))
        self.project.add_event(Event(0, "第三次", ["zhouyan"], "留灯"))
        bible = full_bible(self.project)
        pack = context_pack(self.project, recent=1)
        self.assertIn("第三次", bible)
        self.assertIn("第二次", bible)      # 较早那条只在圣经里
        self.assertNotIn("第二次", pack)    # 最近 1 条不含它
        self.assertGreater(len(bible), len(pack))


class TestPersistence(TempMixin):
    def test_round_trip(self):
        store = Store(self._dir / "p.json")
        project = Project(title="T", premise="P")
        project.add_character(adult("林夏", 29))
        store.save(project)
        loaded = store.load()
        self.assertEqual(loaded.title, "T")
        self.assertEqual(loaded.characters[0].name, "林夏")

    def test_missing_file(self):
        store = Store(self._dir / "nope.json")
        with self.assertRaises(StudioError):
            store.load()

    def test_corrupt_file(self):
        path = self._dir / "bad.json"
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(StudioError):
            Store(path).load()


class TestValidate(unittest.TestCase):
    def test_clean_project_passes(self):
        project = Project()
        project.add_character(adult("林夏", 29, "linxia"))
        project.set_relationship(Relationship("linxia", "linxia", "自省", 1))
        self.assertEqual(validate(project), [])

    def test_detects_dangling_reference(self):
        project = Project()
        project.add_character(adult("林夏", 29, "linxia"))
        # 绕过 add_event 的校验，直接塞一条坏数据
        project.events.append(Event(1, "坏事件", ["ghost"], ""))
        problems = validate(project)
        self.assertTrue(any("不存在的角色" in item for item in problems))

    def test_detects_empty(self):
        self.assertTrue(validate(Project()))


if __name__ == "__main__":
    unittest.main()
