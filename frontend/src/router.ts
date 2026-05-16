import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'
import LoginPage from './pages/LoginPage.vue'
import RegisterPage from './pages/RegisterPage.vue'
import DashboardPage from './pages/DashboardPage.vue'
import BanksPage from './pages/BanksPage.vue'
import PublicBanksPage from './pages/PublicBanksPage.vue'
import BankDetailPage from './pages/BankDetailPage.vue'
import GeneratePage from './pages/GeneratePage.vue'
import GenerationJobsPage from './pages/GenerationJobsPage.vue'
import GenerationDraftPage from './pages/GenerationDraftPage.vue'
import ProfilePage from './pages/ProfilePage.vue'
import AIProvidersPage from './pages/AIProvidersPage.vue'
import QuestionsPage from './pages/QuestionsPage.vue'
import PracticeSetupPage from './pages/PracticeSetupPage.vue'
import PracticeSessionPage from './pages/PracticeSessionPage.vue'
import PracticeResultPage from './pages/PracticeResultPage.vue'
import MistakesPage from './pages/MistakesPage.vue'
import HistoryPage from './pages/HistoryPage.vue'
import UserPublicPage from './pages/UserPublicPage.vue'
import AdminUsersPage from './pages/AdminUsersPage.vue'
import FavoritesPage from './pages/FavoritesPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', component: LoginPage },
    { path: '/register', component: RegisterPage },
    { path: '/dashboard', component: DashboardPage, meta: { auth: true } },
    { path: '/profile', component: ProfilePage, meta: { auth: true } },
    { path: '/users/:userId', component: UserPublicPage, meta: { auth: true } },
    { path: '/banks', component: BanksPage, meta: { auth: true } },
    { path: '/banks/public', component: PublicBanksPage, meta: { auth: true } },
    { path: '/favorites', component: FavoritesPage, meta: { auth: true } },
    { path: '/banks/generate', component: GeneratePage, meta: { auth: true } },
    { path: '/banks/:bankId/generate', component: GeneratePage, meta: { auth: true } },
    { path: '/banks/generation-jobs', component: GenerationJobsPage, meta: { auth: true } },
    { path: '/ai-generation/jobs/:jobId/draft', component: GenerationDraftPage, meta: { auth: true } },
    { path: '/banks/:bankId', component: BankDetailPage, meta: { auth: true } },
    { path: '/banks/:bankId/questions', component: QuestionsPage, meta: { auth: true } },
    { path: '/banks/:bankId/mistakes', component: MistakesPage, meta: { auth: true } },
    { path: '/banks/:bankId/practice/setup', component: PracticeSetupPage, meta: { auth: true } },
    { path: '/practice/session/:sessionId', component: PracticeSessionPage, meta: { auth: true } },
    { path: '/practice/result/:sessionId', component: PracticeResultPage, meta: { auth: true } },
    { path: '/history', component: HistoryPage, meta: { auth: true } },
    { path: '/settings/ai-providers', component: AIProvidersPage, meta: { auth: true } },
    { path: '/admin/users', component: AdminUsersPage, meta: { auth: true } },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (auth.token && !auth.user) {
    try {
      await auth.loadMe()
    } catch {
      auth.logout()
    }
  }
  if (to.meta.auth && !auth.token) return '/login'
})
