export const localDevelopment = import.meta.env.DEV && import.meta.env.VITE_LOCAL_DEV_MODE === 'true' && ['localhost', '127.0.0.1'].includes(location.hostname)
