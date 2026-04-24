import { invoke } from "@tauri-apps/api/core";

export interface Inspiration {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export async function createInspiration(name: string): Promise<Inspiration> {
  return invoke<Inspiration>("create_inspiration", { name });
}

export async function listInspirations(query?: string): Promise<Inspiration[]> {
  return invoke<Inspiration[]>("list_inspirations", { query: query || null });
}

export async function getInspiration(id: string): Promise<Inspiration> {
  return invoke<Inspiration>("get_inspiration", { id });
}

export async function deleteInspiration(id: string): Promise<void> {
  return invoke<void>("delete_inspiration", { id });
}
