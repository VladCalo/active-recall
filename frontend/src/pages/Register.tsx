/**
 * Register Page
 * 
 * Handles new user registration with password requirements.
 * Responsive design with clear validation feedback.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Brain, Mail, Lock, AlertCircle, CheckCircle2, Clock } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/contexts/AuthContext'

const MIN_PASSWORD_LENGTH = 10

export function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [retryAfter, setRetryAfter] = useState<number | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const { register } = useAuth()

  // Password validation
  const hasMinLength = password.length >= MIN_PASSWORD_LENGTH
  const hasUppercase = /[A-Z]/.test(password)
  const hasLowercase = /[a-z]/.test(password)
  const hasNumber = /\d/.test(password)
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password)
  const passwordsMatch = password === confirmPassword && password.length > 0
  
  const passwordStrength = [hasMinLength, hasUppercase, hasLowercase, hasNumber, hasSpecial]
    .filter(Boolean).length
  
  const canSubmit = email && hasMinLength && hasUppercase && hasLowercase && 
                   hasNumber && hasSpecial && passwordsMatch && !isLoading

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setRetryAfter(null)

    if (!passwordsMatch) {
      setError('Passwords do not match')
      return
    }

    setIsLoading(true)

    try {
      const message = await register(email, password)
      setSuccessMessage(message)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Registration failed'
      setError(message)
      
      // Check for rate limiting
      if (message.toLowerCase().includes('too many') || message.toLowerCase().includes('rate limit')) {
        setRetryAfter(600) // 10 minutes for registration
      }
    } finally {
      setIsLoading(false)
    }
  }

  const RequirementItem = ({ met, text }: { met: boolean; text: string }) => (
    <div className="flex items-center gap-2 text-xs sm:text-sm">
      {met ? (
        <CheckCircle2 className="h-3.5 w-3.5 text-green-600 flex-shrink-0" />
      ) : (
        <div className="h-3.5 w-3.5 rounded-full border border-muted-foreground flex-shrink-0" />
      )}
      <span className={met ? 'text-green-600' : 'text-muted-foreground'}>{text}</span>
    </div>
  )

  if (successMessage) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center space-y-2 pb-4">
            <div className="flex justify-center mb-2">
              <div className="p-3 rounded-full bg-green-100">
                <CheckCircle2 className="h-7 w-7 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </div>
            <CardTitle className="text-xl sm:text-2xl">Registration successful</CardTitle>
            <CardDescription className="text-sm">{successMessage}</CardDescription>
          </CardHeader>
          <CardContent className="pb-6 text-center">
            <Link to="/login" className="text-primary hover:underline font-medium text-sm">
              Back to sign in
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center space-y-2 pb-4">
          <div className="flex justify-center mb-2">
            <div className="p-3 rounded-full bg-primary/10">
              <Brain className="h-7 w-7 sm:h-8 sm:w-8 text-primary" />
            </div>
          </div>
          <CardTitle className="text-xl sm:text-2xl">Create an account</CardTitle>
          <CardDescription className="text-sm">
            Start tracking your studies with Active Recall
          </CardDescription>
        </CardHeader>
        <CardContent className="pb-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="flex items-start gap-2 p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <div>
                  <span>{error}</span>
                  {retryAfter && (
                    <div className="flex items-center gap-1 mt-1 text-xs">
                      <Clock className="h-3 w-3" />
                      <span>Try again in {Math.ceil(retryAfter / 60)} minutes</span>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm font-medium">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10 h-11"
                  required
                  autoComplete="email"
                  disabled={isLoading}
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm font-medium">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 h-11"
                  required
                  autoComplete="new-password"
                  disabled={isLoading}
                />
              </div>
              
              {/* Password requirements - always visible */}
              <div className="mt-2 space-y-2">
                {password && (
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((level) => (
                      <div
                        key={level}
                        className={`h-1 flex-1 rounded-full transition-colors ${
                          passwordStrength >= level
                            ? passwordStrength <= 2
                              ? 'bg-red-500'
                              : passwordStrength <= 3
                              ? 'bg-yellow-500'
                              : 'bg-green-500'
                            : 'bg-muted'
                        }`}
                      />
                    ))}
                  </div>
                )}
                <div className="grid gap-1 p-2 bg-muted/50 rounded-md">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Password must have:</p>
                  <RequirementItem met={hasMinLength} text={`At least ${MIN_PASSWORD_LENGTH} characters`} />
                  <RequirementItem met={hasUppercase} text="Uppercase letter (A-Z)" />
                  <RequirementItem met={hasLowercase} text="Lowercase letter (a-z)" />
                  <RequirementItem met={hasNumber} text="Number (0-9)" />
                  <RequirementItem met={hasSpecial} text="Special character (!@#$%...)" />
                </div>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="confirmPassword" className="text-sm font-medium">Confirm Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="pl-10 h-11"
                  required
                  autoComplete="new-password"
                  disabled={isLoading}
                />
              </div>
              {confirmPassword && (
                <div className="flex items-center gap-2 text-xs sm:text-sm">
                  {passwordsMatch ? (
                    <>
                      <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
                      <span className="text-green-600">Passwords match</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="h-3.5 w-3.5 text-destructive" />
                      <span className="text-destructive">Passwords do not match</span>
                    </>
                  )}
                </div>
              )}
            </div>
            
            <Button 
              type="submit" 
              className="w-full h-11 text-base" 
              disabled={!canSubmit || !!retryAfter}
            >
              {isLoading ? 'Creating account...' : 'Create account'}
            </Button>
          </form>
          
          <div className="mt-6 text-center text-sm">
            <span className="text-muted-foreground">Already have an account? </span>
            <Link to="/login" className="text-primary hover:underline font-medium">
              Sign in
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
