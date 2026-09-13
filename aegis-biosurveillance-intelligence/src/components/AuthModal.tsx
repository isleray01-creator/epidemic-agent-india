import React, { useState } from 'react';
import { UserProfile } from '../types';
import { Shield, Lock, Mail, User, Building, Award, CheckCircle, X } from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: UserProfile | null;
  onLogin: (user: UserProfile) => void;
  onLogout: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onLogin,
  onLogout,
}) => {
  const [tab, setTab] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState<UserProfile['role']>('Chief Epidemiologist');
  const [organization, setOrganization] = useState('ICMR - National Institute of Virology');
  const [credentialId, setCredentialId] = useState('AEGIS-NIV-2026-');
  const [errorMsg, setErrorMsg] = useState('');

  if (!isOpen) return null;

  const handleDemoLogin = (profileType: 'swaminathan' | 'biostat' | 'command') => {
    let demoUser: UserProfile;
    if (profileType === 'swaminathan') {
      demoUser = {
        id: 'usr-9288-in',
        name: 'Dr. V. Swaminathan, FAMS, DSc',
        email: 'swaminathan.v@aegis-surveillance.gov.in',
        role: 'Chief Epidemiologist',
        credentialId: 'AEGIS-AUTH-IND-2026-981',
        clearanceLevel: 'OFFICIAL CLINICAL // DEF-4',
        organization: 'National Biosecurity & Epidemiologic Command (NDMA/ICMR)',
        verifiedAt: new Date().toISOString(),
      };
    } else if (profileType === 'biostat') {
      demoUser = {
        id: 'usr-4112-in',
        name: 'Dr. Priya Sen, PhD',
        email: 'p.sen@biostat.icmr.res.in',
        role: 'Lead Biostatistician',
        credentialId: 'BIOSTAT-PINN-2026-412',
        clearanceLevel: 'RESEARCH CLINICAL // DEF-3',
        organization: 'Department of Mathematical Epidemiology & PINN Labs',
        verifiedAt: new Date().toISOString(),
      };
    } else {
      demoUser = {
        id: 'usr-6031-in',
        name: 'Brig. Alok Sharma, MD',
        email: 'a.sharma@def-health.gov.in',
        role: 'Clinical Officer',
        credentialId: 'MIL-BIOSEC-2026-809',
        clearanceLevel: 'STRATEGIC SURVEILLANCE // DEF-5',
        organization: 'Integrated Defense Biosecurity & Pandemic Command',
        verifiedAt: new Date().toISOString(),
      };
    }
    onLogin(demoUser);
    onClose();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !email.includes('@')) {
      setErrorMsg('Please provide a valid institutional email address.');
      return;
    }
    if (password.length < 6) {
      setErrorMsg('Access token / password must be at least 6 characters.');
      return;
    }

    if (tab === 'login') {
      const loggedUser: UserProfile = {
        id: `usr-${Math.floor(Math.random() * 9000 + 1000)}`,
        name: name || (email.split('@')[0].toUpperCase() + ' (Epidemiology)'),
        email,
        role: role || 'Chief Epidemiologist',
        credentialId: `AEGIS-${Math.random().toString(36).substring(2, 7).toUpperCase()}-2026`,
        clearanceLevel: 'OFFICIAL CLINICAL // DEF-4',
        organization: organization || 'National Center for Disease Control',
        verifiedAt: new Date().toISOString(),
      };
      onLogin(loggedUser);
      onClose();
    } else {
      if (!name) {
        setErrorMsg('Please enter your full name and clinical qualifications.');
        return;
      }
      const newUser: UserProfile = {
        id: `usr-${Math.floor(Math.random() * 9000 + 1000)}`,
        name,
        email,
        role,
        credentialId: credentialId.length > 5 ? credentialId : `AEGIS-REG-${Date.now().toString().slice(-4)}`,
        clearanceLevel: 'OFFICIAL CLINICAL // DEF-4',
        organization,
        verifiedAt: new Date().toISOString(),
      };
      onLogin(newUser);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div 
        id="auth-modal-card"
        className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="p-5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-[#0d3b36] text-white flex items-center justify-center shadow-sm">
              <Shield className="w-5 h-5 text-teal-300" />
            </div>
            <div>
              <h3 className="font-headline font-bold text-base text-slate-900">
                EpiPulse Account Access
              </h3>
              <p className="text-[11px] text-slate-500 font-mono">
                SIGN IN TO YOUR ACCOUNT
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 flex items-center justify-center"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* If user is already logged in */}
        {currentUser ? (
          <div className="p-6 space-y-5">
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-3">
              <CheckCircle className="w-6 h-6 text-emerald-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-900 text-sm">{currentUser.name}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                    VERIFIED
                  </span>
                </div>
                <p className="text-xs text-slate-600">{currentUser.email}</p>
                <div className="text-[11px] font-mono text-slate-500 pt-1">
                  <div>ROLE: <span className="text-slate-800 font-bold">{currentUser.role}</span></div>
                  <div>ID: <span className="text-[#0d3b36] font-bold">{currentUser.credentialId}</span></div>
                  <div>CLEARANCE: <span className="text-emerald-700 font-bold">{currentUser.clearanceLevel}</span></div>
                  <div>INSTITUTE: {currentUser.organization}</div>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={onLogout}
                className="flex-1 py-2.5 rounded-xl border border-red-200 bg-red-50 hover:bg-red-100 text-red-700 text-xs font-bold transition-colors"
              >
                Sign Out of Command
              </button>
              <button
                onClick={onClose}
                className="flex-1 py-2.5 rounded-xl bg-[#0d3b36] hover:bg-[#082623] text-white text-xs font-bold transition-colors shadow-sm"
              >
                Return to Dashboard
              </button>
            </div>
          </div>
        ) : (
          /* Sign In / Sign Up Tabs */
          <div className="p-6 space-y-4">
            {/* Quick Demo Logins */}
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-2">
                Fast-Track Clinical Demo Profiles
              </span>
              <div className="grid grid-cols-3 gap-1.5">
                <button
                  type="button"
                  onClick={() => handleDemoLogin('swaminathan')}
                  className="px-2 py-1.5 rounded-lg bg-white border border-slate-200 hover:border-[#0d3b36] text-[11px] font-semibold text-slate-700 hover:text-[#0d3b36] text-left leading-tight transition-all shadow-2xs"
                >
                  <span className="font-bold block text-slate-900 truncate">Dr. Swaminathan</span>
                  <span className="text-[9px] text-slate-400">Chief Officer</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDemoLogin('biostat')}
                  className="px-2 py-1.5 rounded-lg bg-white border border-slate-200 hover:border-[#0d3b36] text-[11px] font-semibold text-slate-700 hover:text-[#0d3b36] text-left leading-tight transition-all shadow-2xs"
                >
                  <span className="font-bold block text-slate-900 truncate">Dr. Priya Sen</span>
                  <span className="text-[9px] text-slate-400">Biostatistician</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDemoLogin('command')}
                  className="px-2 py-1.5 rounded-lg bg-white border border-slate-200 hover:border-[#0d3b36] text-[11px] font-semibold text-slate-700 hover:text-[#0d3b36] text-left leading-tight transition-all shadow-2xs"
                >
                  <span className="font-bold block text-slate-900 truncate">Brig. Sharma</span>
                  <span className="text-[9px] text-slate-400">Public Health</span>
                </button>
              </div>
            </div>

            {/* Tab switch */}
            <div className="flex rounded-lg bg-slate-100 p-1 border border-slate-200">
              <button
                type="button"
                onClick={() => { setTab('login'); setErrorMsg(''); }}
                className={`flex-1 py-1.5 rounded-md text-xs font-bold transition-all ${
                  tab === 'login' ? 'bg-white text-[#0d3b36] shadow-xs' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Officer Login
              </button>
              <button
                type="button"
                onClick={() => { setTab('signup'); setErrorMsg(''); }}
                className={`flex-1 py-1.5 rounded-md text-xs font-bold transition-all ${
                  tab === 'signup' ? 'bg-white text-[#0d3b36] shadow-xs' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                Register Officer
              </button>
            </div>

            {errorMsg && (
              <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs font-medium">
                {errorMsg}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-3">
              {tab === 'signup' && (
                <>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                      Full Name & Title
                    </label>
                    <div className="relative flex items-center">
                      <User className="w-4 h-4 absolute left-3 text-slate-400 pointer-events-none" />
                      <input
                        type="text"
                        required
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Dr. Anandita Roy, MD (Epidemiology)"
                        className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0d9488]"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                        Clinical Role
                      </label>
                      <select
                        value={role}
                        onChange={(e) => setRole(e.target.value as any)}
                        className="w-full px-2.5 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0d9488]"
                      >
                        <option value="Chief Epidemiologist">Chief Epidemiologist</option>
                        <option value="Lead Biostatistician">Lead Biostatistician</option>
                        <option value="Clinical Officer">Clinical Officer</option>
                        <option value="Public Health Analyst">Public Health Analyst</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                        License / ID
                      </label>
                      <div className="relative flex items-center">
                        <Award className="w-4 h-4 absolute left-2.5 text-slate-400 pointer-events-none" />
                        <input
                          type="text"
                          value={credentialId}
                          onChange={(e) => setCredentialId(e.target.value)}
                          placeholder="MCI-2026-99"
                          className="w-full pl-8 pr-2.5 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0d9488]"
                        />
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                      Healthcare Affiliation
                    </label>
                    <div className="relative flex items-center">
                      <Building className="w-4 h-4 absolute left-3 text-slate-400 pointer-events-none" />
                      <input
                        type="text"
                        value={organization}
                        onChange={(e) => setOrganization(e.target.value)}
                        placeholder="ICMR / AIIMS / State Health Directorate"
                        className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0d9488]"
                      />
                    </div>
                  </div>
                </>
              )}

              <div>
                <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                  Institutional Email
                </label>
                <div className="relative flex items-center">
                  <Mail className="w-4 h-4 absolute left-3 text-slate-400 pointer-events-none" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="officer@aegis-surveillance.gov.in"
                    className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0d9488]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                  Security Passkey / Password
                </label>
                <div className="relative flex items-center">
                  <Lock className="w-4 h-4 absolute left-3 text-slate-400 pointer-events-none" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0d9488]"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full mt-2 py-2.5 rounded-xl bg-[#0d3b36] hover:bg-[#082623] text-white text-xs font-bold shadow-md hover:shadow transition-all"
              >
                {tab === 'login' ? 'Authenticate & Access Surveillance' : 'Register Clinical Profile'}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};
