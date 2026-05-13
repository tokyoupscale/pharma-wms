import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useThemeStore = create(
  persist(
    (set) => ({
      isDark: false,
      toggle: () => set((s) => ({ isDark: !s.isDark })),
    }),
    { name: 'vilar-theme' }
  )
)
