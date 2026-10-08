import {
  createClient,
  type Session,
  type SupabaseClient,
} from "@supabase/supabase-js";
import { env } from "../config/env";

let supabaseClient: SupabaseClient | null = null;

function getSupabaseClient(): SupabaseClient {
  if (supabaseClient) {
    return supabaseClient;
  }

  if (!env.supabaseUrl) {
    throw new Error("VITE_SUPABASE_URL is not configured");
  }

  if (!env.supabaseAnonKey) {
    throw new Error(
      "VITE_SUPABASE_ANON_KEY is not configured",
    );
  }

  supabaseClient = createClient(
    env.supabaseUrl,
    env.supabaseAnonKey,
  );

  return supabaseClient;
}

export async function signIn(
  email: string,
  password: string,
): Promise<Session> {
  const { data, error } =
    await getSupabaseClient().auth.signInWithPassword({
      email,
      password,
    });

  if (error) {
    throw new Error(error.message);
  }

  if (!data.session) {
    throw new Error("Supabase login did not return a session");
  }

  return data.session;
}

export async function signOut(): Promise<void> {
  const { error } =
    await getSupabaseClient().auth.signOut();

  if (error) {
    throw new Error(error.message);
  }
}

export async function getSession(): Promise<Session | null> {
  const { data, error } =
    await getSupabaseClient().auth.getSession();

  if (error) {
    throw new Error(error.message);
  }

  return data.session;
}

export function subscribeToAuthChanges(
  callback: (session: Session | null) => void,
): () => void {
  const {
    data: { subscription },
  } = getSupabaseClient().auth.onAuthStateChange(
    (_event, session) => {
      callback(session);
    },
  );

  return () => {
    subscription.unsubscribe();
  };
}