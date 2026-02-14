/**
 * Supabase Client for Server Components
 *
 * This creates a Supabase client for use in server-side React components
 * and API routes. Uses the service role key for admin operations.
 *
 * IMPORTANT: Only use this on the server side!
 */

import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { Database } from './types'

export const createServerSupabaseClient = async () => {
  const cookieStore = await cookies()

  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!, // Use service role for server-side
    {
      cookies: {
        get(name: string) {
          return cookieStore.get(name)?.value
        },
        set(name: string, value: string, options: any) {
          try {
            cookieStore.set({ name, value, ...options })
          } catch {
            // In server components, cookies are read-only
          }
        },
        remove(name: string, options: any) {
          try {
            cookieStore.set({ name, value: '', ...options })
          } catch {
            // In server components, cookies are read-only
          }
        },
      },
    }
  )
}

// Helper function to get client with service role for admin operations
export const getAdminSupabaseClient = () => {
  const { createClient } = require('@supabase/supabase-js')
  const { Database } = require('./types')

  return createClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  )
}

export default createServerSupabaseClient
