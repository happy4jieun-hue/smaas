import { createRouter, createWebHistory } from "vue-router";
import AdminDashboard       from "./pages/AdminDashboard.vue";
import AdminReviewPage      from "./pages/AdminReviewPage.vue";
import AssignmentReviewPage from "./pages/AssignmentReviewPage.vue";
import CreateTaskPage       from "./pages/CreateTaskPage.vue";
import MembersPage          from "./pages/MembersPage.vue";
import MyTaskDetailPage     from "./pages/MyTaskDetailPage.vue";
import MyTasksPage          from "./pages/MyTasksPage.vue";
import NotificationsPage    from "./pages/NotificationsPage.vue";
import TaskListPage         from "./pages/TaskListPage.vue";
import WorkflowResultPage   from "./pages/WorkflowResultPage.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // 공용
    { path: "/",                              component: TaskListPage },
    { path: "/tasks/new",                     component: CreateTaskPage },
    { path: "/workflows/:taskId",             component: WorkflowResultPage },
    { path: "/tasks/:taskId/assignments",     component: AssignmentReviewPage },

    // 관리자
    { path: "/admin",                         component: AdminDashboard },
    { path: "/admin/review",                  component: AdminReviewPage },
    { path: "/admin/notifications",           component: NotificationsPage },
    { path: "/members",                       component: MembersPage },

    // 기존 라우트 redirect (북마크/링크 호환)
    { path: "/admin/plans",    redirect: "/admin/review" },
    { path: "/admin/progress", redirect: "/admin/review" },
    { path: "/admin/rejected", redirect: "/admin/review" },

    // worker
    { path: "/my-tasks",                      component: MyTasksPage },
    { path: "/my-tasks/:id",                  component: MyTaskDetailPage },
    { path: "/notifications",                 component: NotificationsPage },
  ],
});

export default router;
