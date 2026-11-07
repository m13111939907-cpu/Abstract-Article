import { createRouter, createWebHistory } from 'vue-router'

import DashboardView from '../views/DashboardView.vue'
import GraphExplorerView from '../views/GraphExplorerView.vue'
import PaperView from '../views/PaperView.vue'
import PapersView from '../views/PapersView.vue'
import ProjectDetailView from '../views/ProjectDetailView.vue'
import ProjectsView from '../views/ProjectsView.vue'
import SettingsView from '../views/SettingsView.vue'
import SourcesView from '../views/SourcesView.vue'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: (to, from, savedPosition) => savedPosition || { top: 0 },
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView,
      meta: { title: '概览', section: '工作台' },
    },
    {
      path: '/projects',
      name: 'projects',
      component: ProjectsView,
      meta: { title: '研究项目', section: '工作台' },
    },
    {
      path: '/projects/:id',
      name: 'project',
      component: ProjectDetailView,
      meta: { title: '项目详情', section: '工作台' },
    },
    {
      path: '/papers',
      name: 'papers',
      component: PapersView,
      meta: { title: '文献库', section: '工作台' },
    },
    {
      path: '/papers/:id',
      name: 'paper',
      component: PaperView,
      meta: { title: '文献阅读', section: '工作台' },
    },
    {
      path: '/graph',
      name: 'graph',
      component: GraphExplorerView,
      meta: { title: '知识图谱', section: '工作台' },
    },
    {
      path: '/sources',
      name: 'sources',
      component: SourcesView,
      meta: { title: '订阅源', section: '系统' },
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
      meta: { title: '设置', section: '系统' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.afterEach((to) => {
  document.title = `${to.meta.title || '工作台'} · 文献提取器`
})

export default router
