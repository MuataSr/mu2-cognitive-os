/**
 * Supabase Client for Browser/Client Components
 *
 * This creates a Supabase client for use in client-side React components.
 * Uses the anon key for public operations.
 */

import { createClientComponentClient } from '@supabase/supabase-js'
import { Database } from './types'

export const createClient = () => {
  return createClientComponentClient<Database>({
    supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL!,
    supabaseKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  })
}

// Singleton instance for client components
let clientInstance: ReturnType<typeof createClient> | null = null

export const getSupabaseClient = () => {
  if (!clientInstance) {
    clientInstance = createClient()
  }
  return clientInstance
}

// Default export
export default getSupabaseClient
