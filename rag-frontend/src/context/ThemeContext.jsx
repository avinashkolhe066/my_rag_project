import React, { createContext, useContext, useState, useEffect } from 'react'
const ThemeContext = createContext()
export function ThemeProvider({ children }) {
    const [dark, setDark] = useState(() => localStorage.getItem('rag_theme') !== 'light')
    useEffect(() => {
        document.documentElement.classList.toggle('dark', dark)
        localStorage.setItem('rag_theme', dark ? 'dark' : 'light')
    }, [dark])
    return <ThemeContext.Provider value={{ dark, toggle: () => setDark(p => !p) }}>{children}</ThemeContext.Provider>
}
export const useTheme = () => useContext(ThemeContext)