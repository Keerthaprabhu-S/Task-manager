from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

PW = "Str0ngPass!9"

def make_client(name):
    c = APIClient()
    c.post("/api/auth/register/", {"username": name, "email": f"{name}@x.com", "password": PW}, format="json")
    return c

class PlannerTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.a, self.b = make_client("alice"), make_client("bobby")
        self.today = timezone.localdate()

    def task(self, c=None, **kw):
        r = (c or self.a).post("/api/tasks/", {"title": "T", **kw}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def test_validation_error_envelope(self):
        r = self.a.post("/api/tasks/", {"title": "  "}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["error"]["status"], 400)

    def test_users_only_see_own_data(self):
        t = self.task()
        self.assertEqual(self.b.get(f"/api/tasks/{t['id']}/").status_code, 404)
        self.assertEqual(self.b.get("/api/tasks/").data["count"], 0)

    def test_views_and_filters(self):
        self.task(title="today", due_date=str(self.today))
        self.task(title="old", due_date=str(self.today - timedelta(days=2)), priority="high")
        self.task(title="later", due_date=str(self.today + timedelta(days=2)))
        self.assertEqual(self.a.get("/api/tasks/?view=today").data["count"], 1)
        self.assertEqual(self.a.get("/api/tasks/?view=overdue").data["count"], 1)
        self.assertEqual(self.a.get("/api/tasks/?view=upcoming").data["count"], 1)
        self.assertEqual(self.a.get("/api/tasks/?priority=high").data["count"], 1)
        self.assertEqual(self.a.get("/api/tasks/?search=lat").data["count"], 1)

    def test_recurring_task_spawns_next_on_completion(self):
        t = self.task(due_date=str(self.today), recurrence="daily")
        r = self.a.patch(f"/api/tasks/{t['id']}/", {"status": "done"}, format="json")
        self.assertIsNotNone(r.data["completed_at"])
        res = self.a.get("/api/tasks/?status=todo").data
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["results"][0]["due_date"], str(self.today + timedelta(days=1)))

    def test_goal_progress_and_cross_user_link_blocked(self):
        g = self.a.post("/api/goals/", {"title": "G"}, format="json").data
        t1, _ = self.task(goal=g["id"]), self.task(goal=g["id"])
        self.a.post("/api/milestones/", {"goal": g["id"], "title": "M"}, format="json")
        self.a.patch(f"/api/tasks/{t1['id']}/", {"status": "done"}, format="json")
        self.assertEqual(self.a.get(f"/api/goals/{g['id']}/").data["progress"]["percent"], 33)
        r = self.b.post("/api/tasks/", {"title": "x", "goal": g["id"]}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_dashboard_and_reminders(self):
        t = self.task(due_date=str(self.today))
        self.task(due_date=str(self.today - timedelta(days=1)))
        self.assertEqual(len(self.a.get("/api/reminders/").data), 2)
        self.a.patch(f"/api/tasks/{t['id']}/", {"status": "done"}, format="json")
        d = self.a.get("/api/dashboard/").data
        self.assertEqual(d["streak"], 1)
        self.assertEqual(d["overdue_count"], 1)
        self.assertEqual(d["weekly"][-1]["count"], 1)
