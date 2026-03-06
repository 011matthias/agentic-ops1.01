import type { Card, Project } from '../types/index.ts';

const BASE = '/api'; // Vite proxies to localhost:3001

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return undefined as T;
  if (!res.ok) throw new Error(`API ${method} ${path} → ${res.status}`);
  return res.json();
}

export const api = {
  projects: {
    list:   ()                                          => req<Project[]>('GET', '/projects'),
    create: (id: string, name: string, color: string)  => req<Project>('POST', '/projects', { id, name, color }),
    update: (id: string, patch: Partial<Project>)       => req<Project>('PATCH', `/projects/${id}`, patch),
    delete: (id: string)                                => req<void>('DELETE', `/projects/${id}`),
  },
  cards: {
    list:   (projectId?: string) => req<Card[]>('GET', `/cards${projectId ? `?projectId=${projectId}` : ''}`),
    create: (id: string, projectId: string, columnId: string, title: string) =>
      req<Card>('POST', '/cards', { id, projectId, columnId, title }),
    update: (id: string, patch: Partial<Card>) => req<Card>('PATCH', `/cards/${id}`, patch),
    delete: (id: string)                        => req<void>('DELETE', `/cards/${id}`),
  },
  boardState: {
    get: () => req<unknown>('GET', '/board-state'),
  },
};
