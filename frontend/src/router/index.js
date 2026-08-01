import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    redirect: '/overview',
    children: [
      {
        path: 'overview',
        name: 'Overview',
        component: () => import('@/views/Overview.vue'),
        meta: { title: '现场闭环总览', icon: 'DataAnalysis' }
      },
      {
        path: 'signs',
        name: 'Signs',
        component: () => import('@/views/SignList.vue'),
        meta: { title: '位标准入核验', icon: 'Tickets' }
      },
      {
        path: 'issue',
        name: 'Issue',
        component: () => import('@/views/Issue.vue'),
        meta: { title: '入场定位投放', icon: 'Promotion' }
      },
      {
        path: 'recycle',
        name: 'Recycle',
        component: () => import('@/views/Recycle.vue'),
        meta: { title: '散场归位核验', icon: 'Refresh' }
      },
      {
        path: 'review',
        name: 'Review',
        component: () => import('@/views/Review.vue'),
        meta: { title: '防错复核', icon: 'DocumentChecked' }
      },
      {
        path: 'anomaly',
        name: 'Anomaly',
        component: () => import('@/views/Anomaly.vue'),
        meta: { title: '偏差闭环核销', icon: 'Warning' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && userStore.isLoggedIn) {
    next('/overview')
  } else {
    next()
  }
})

export default router
