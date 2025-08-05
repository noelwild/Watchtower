import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';

// Import UI components
import { Button } from './components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Badge } from './components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Textarea } from './components/ui/textarea';
import { Switch } from './components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Avatar, AvatarFallback } from './components/ui/avatar';
import { Progress } from './components/ui/progress';

// Icons
import { 
  Shield, 
  Users, 
  Calendar, 
  AlertTriangle, 
  Settings, 
  Clock, 
  TrendingUp,
  UserCheck,
  Eye,
  LogOut,
  Car,
  Building,
  Moon,
  Coffee,
  Timer,
  BarChart3,
  X,
  CheckCircle,
  Activity,
  GraduationCap,
  Scale,
  XCircle,
  Zap,
  User,
  FileText,
  TrendingDown,
  MapPin,
  Phone,
  Mail,
  Calendar2,
  History,
  Target,
  Award,
  Brain,
  Heart
} from 'lucide-react';

// Configuration - Use relative URLs for Kubernetes ingress routing
// Kubernetes automatically routes /api requests to backend port 8001
const BACKEND_URL = ''; // Use same origin
const API = `/api`;

// Authentication context
const AuthContext = React.createContext();

// Date formatting utility
const formatDate = (date) => {
  if (!date) return 'N/A';
  const d = new Date(date);
  const day = d.getDate().toString().padStart(2, '0');
  const month = (d.getMonth() + 1).toString().padStart(2, '0');
  const year = d.getFullYear();
  return `${day}/${month}/${year}`;
};

// Date and time formatting utility
const formatDateTime = (date) => {
  if (!date) return 'N/A';
  const d = new Date(date);
  const day = d.getDate().toString().padStart(2, '0');
  const month = (d.getMonth() + 1).toString().padStart(2, '0');
  const year = d.getFullYear();
  const hours = d.getHours().toString().padStart(2, '0');
  const minutes = d.getMinutes().toString().padStart(2, '0');
  return `${day}/${month}/${year} ${hours}:${minutes}`;
};

// Enhanced Category Detail Modal Component - Single Static Window
const CategoryDetailModal = ({ category, isOpen, onClose, onViewDetails }) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && category) {
      fetchCategoryData();
    }
  }, [isOpen, category]);

  const fetchCategoryData = async () => {
    setLoading(true);
    try {
      let endpoint = '';
      switch (category.type) {
        case 'high_fatigue':
          endpoint = '/analytics/high-fatigue-members';
          break;
        case 'eba_violations':
          endpoint = '/analytics/eba-violations-detail';
          break;
        case 'eba_warnings':
          endpoint = '/analytics/eba-warnings-detail';
          break;
        case 'eba_compliant':
          endpoint = '/analytics/eba-compliant-members';
          break;
        case 'over_76_hours':
          endpoint = '/analytics/over-76-hours';
          break;
        case 'approaching_76_hours':
          endpoint = '/analytics/approaching-76-hours';
          break;
        case 'night_recovery':
          endpoint = '/analytics/night-recovery-issues';
          break;
        case 'rest_day_issues':
          endpoint = '/analytics/rest-day-issues';
          break;
        case 'overdue_corro':
          endpoint = '/analytics/corro-distribution';
          break;
        case 'leave_requests':
          endpoint = '/leave-requests?status=pending';
          break;
        case 'training_expiring':
          endpoint = '/training/expiring';
          break;
        case 'court_dates':
          endpoint = '/court-dates';
          break;
        default:
          return;
      }
      
      const response = await axios.get(`${API}${endpoint}`);
      
      // Sort by urgency for all welfare indicators
      let sortedData = response.data;
      if (category.type === 'overdue_corro') {
        sortedData = response.data
          .filter(m => m.overdue)
          .sort((a, b) => (b.days_since_corro || 0) - (a.days_since_corro || 0)); // Most overdue first
      } else if (category.type === 'eba_violations' || category.type === 'eba_warnings') {
        sortedData = response.data.sort((a, b) => {
          // Sort by violation count first, then by fatigue score
          const aViolations = (a.compliance?.violations?.length || 0);
          const bViolations = (b.compliance?.violations?.length || 0);
          if (aViolations !== bViolations) return bViolations - aViolations;
          return (b.compliance?.fatigue_score || 0) - (a.compliance?.fatigue_score || 0);
        });
      } else if (category.type === 'eba_compliant') {
        sortedData = response.data.sort((a, b) => (a.compliance?.fatigue_score || 0) - (b.compliance?.fatigue_score || 0)); // Lowest fatigue first for compliant
      } else if (category.type === 'over_76_hours' || category.type === 'approaching_76_hours') {
        sortedData = response.data.sort((a, b) => (b.compliance?.fortnight_hours || 0) - (a.compliance?.fortnight_hours || 0)); // Most hours first
      } else if (category.type === 'high_fatigue') {
        sortedData = response.data.sort((a, b) => (b.compliance?.fatigue_score || 0) - (a.compliance?.fatigue_score || 0));
      } else if (category.type === 'rest_day_issues') {
        sortedData = response.data.sort((a, b) => (b.rest_day_deficit || 0) - (a.rest_day_deficit || 0));
      } else if (category.type === 'night_recovery') {
        sortedData = response.data.sort((a, b) => (b.consecutive_nights || 0) - (a.consecutive_nights || 0));
      }
      
      setData(sortedData);
    } catch (error) {
      console.error('Failed to fetch category data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  // Static window positioning - no X button, just content
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
        <div className="bg-gradient-to-r from-slate-800 to-slate-900 text-white p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">{category.title}</h2>
              <p className="text-slate-300 mt-1">{data.length} items found • Sorted by urgency</p>
            </div>
            <div className="flex items-center space-x-4">
              <Badge className="bg-white/20 text-white border-white/30">
                {getUrgencyLevel(category.type, data.length)}
              </Badge>
              <Button 
                onClick={onClose} 
                variant="outline" 
                className="bg-white/10 border-white/30 text-white hover:bg-white/20"
              >
                Close
              </Button>
            </div>
          </div>
        </div>
        
        <div className="overflow-y-auto max-h-[calc(90vh-120px)]">
          {loading ? (
            <div className="flex justify-center p-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <div className="p-6">
              {data.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                  <CheckCircle className="w-16 h-16 mx-auto mb-4 text-green-500" />
                  <h3 className="text-lg font-semibold mb-2">All Clear!</h3>
                  <p>No {category.title.toLowerCase()} requiring attention.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {data.map((item, index) => (
                    <Card key={index} className="hover:shadow-lg transition-all duration-300 border-l-4" 
                          style={{borderLeftColor: getUrgencyColor(category.type, item, index)}}>
                      <CardContent className="p-6">
                        <div className="flex justify-between items-start mb-4">
                          <div className="flex-1">
                            <h3 className="font-bold text-lg flex items-center space-x-2">
                              <span>{item.member_name || item.name}</span>
                              {index < 3 && <span className="text-red-500 text-sm">🚨 URGENT</span>}
                            </h3>
                            <p className="text-slate-600 flex items-center space-x-2 mt-1">
                              <Building className="w-4 h-4" />
                              <span>{item.rank} • {item.station}</span>
                              {item.compliance?.fatigue_score && (
                                <>
                                  <Activity className="w-4 h-4" />
                                  <span>Fatigue: {item.compliance.fatigue_score.toFixed(1)}/100</span>
                                </>
                              )}
                            </p>
                          </div>
                          <div className="text-right">
                            <Badge className={`${getCategoryBadgeColor(category.type)} text-white mb-2`}>
                              {getCategoryBadgeText(category.type, item)}
                            </Badge>
                            <p className="text-xs text-slate-500">#{index + 1} priority</p>
                          </div>
                        </div>

                        {/* Dynamic Content Based on Category */}
                        {renderCategorySpecificContent(category.type, item)}

                        {/* Action Buttons */}
                        <div className="mt-6 flex space-x-2">
                          <Button 
                            size="sm" 
                            className="bg-blue-600 hover:bg-blue-700 text-white"
                            onClick={() => onViewDetails(item)}
                          >
                            <Eye className="w-3 h-3 mr-1" />
                            View Details
                          </Button>
                          {category.type === 'leave_requests' && (
                            <>
                              <Button size="sm" variant="outline" className="text-green-700 border-green-300 hover:bg-green-50">
                                <CheckCircle className="w-3 h-3 mr-1" />
                                Approve
                              </Button>
                              <Button size="sm" variant="outline" className="text-red-700 border-red-300 hover:bg-red-50">
                                <XCircle className="w-3 h-3 mr-1" />
                                Deny
                              </Button>
                            </>
                          )}
                          {category.type === 'eba_violations' && (
                            <Button size="sm" variant="outline" className="text-orange-700 border-orange-300 hover:bg-orange-50">
                              <AlertTriangle className="w-3 h-3 mr-1" />
                              Create Alert
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Helper function to render category-specific content
const renderCategorySpecificContent = (categoryType, item) => {
  switch (categoryType) {
    case 'eba_violations':
      return (
        <div className="space-y-3">
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <h4 className="font-medium text-red-800 text-sm mb-2">EBA Violations ({item.compliance?.violations?.length || 0})</h4>
            {item.compliance?.violations?.slice(0, 2).map((violation, idx) => (
              <p key={idx} className="text-xs text-red-700 mb-1">• {violation}</p>
            ))}
            {(item.compliance?.violations?.length || 0) > 2 && (
              <p className="text-xs text-red-600 font-semibold">+{item.compliance.violations.length - 2} more violations</p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>Fortnight Hours: <strong className="text-red-600">{item.compliance?.fortnight_hours?.toFixed(1)}h / 76h</strong></div>
            <div>Wellness Score: <strong>{item.compliance?.wellness_score?.toFixed(1)}/100</strong></div>
          </div>
        </div>
      );
    
    case 'eba_warnings':
      return (
        <div className="space-y-3">
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
            <h4 className="font-medium text-orange-800 text-sm mb-2">EBA Warnings ({item.compliance?.warnings?.length || 0})</h4>
            {item.compliance?.warnings?.slice(0, 2).map((warning, idx) => (
              <p key={idx} className="text-xs text-orange-700 mb-1">• {warning}</p>
            ))}
            {(item.compliance?.warnings?.length || 0) > 2 && (
              <p className="text-xs text-orange-600 font-semibold">+{item.compliance.warnings.length - 2} more warnings</p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>Fortnight Hours: <strong className="text-orange-600">{item.compliance?.fortnight_hours?.toFixed(1)}h / 76h</strong></div>
            <div>Wellness Score: <strong>{item.compliance?.wellness_score?.toFixed(1)}/100</strong></div>
          </div>
        </div>
      );
    
    case 'eba_compliant':
      return (
        <div className="space-y-3">
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <h4 className="font-medium text-green-800 text-sm mb-2">EBA Compliant - Good Standing</h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>Fortnight Hours: <strong className="text-green-600">{item.compliance?.fortnight_hours?.toFixed(1)}h / 76h</strong></div>
              <div>Wellness Score: <strong>{item.compliance?.wellness_score?.toFixed(1)}/100</strong></div>
              <div>Rest Days: <strong>✅ Compliant</strong></div>
              <div>Break Requirements: <strong>✅ Met</strong></div>
            </div>
          </div>
        </div>
      );
    
    case 'over_76_hours':
      return (
        <div className="space-y-3">
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <h4 className="font-medium text-red-800 text-sm mb-2">Over 76 Hour Limit - EBA Breach</h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>Fortnight Hours: <strong className="text-red-600">{item.compliance?.fortnight_hours?.toFixed(1)}h / 76h</strong></div>
              <div>Overage: <strong className="text-red-600">+{(item.compliance?.fortnight_hours - 76).toFixed(1)}h</strong></div>
              <div>Status: <strong className="text-red-600">🚨 EBA VIOLATION</strong></div>
              <div>Action: <strong>Immediate roster adjustment required</strong></div>
            </div>
          </div>
        </div>
      );
    
    case 'approaching_76_hours':
      return (
        <div className="space-y-3">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <h4 className="font-medium text-yellow-800 text-sm mb-2">Approaching 76 Hour Limit</h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>Fortnight Hours: <strong className="text-yellow-600">{item.compliance?.fortnight_hours?.toFixed(1)}h / 76h</strong></div>
              <div>Remaining: <strong className="text-yellow-600">{(76 - item.compliance?.fortnight_hours).toFixed(1)}h</strong></div>
              <div>Status: <strong className="text-yellow-600">⚠️ MONITOR CLOSELY</strong></div>
              <div>Recommendation: <strong>Limit additional shifts</strong></div>
            </div>
          </div>
        </div>
      );
    
    case 'overdue_corro':
      return (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>Last Corro: <strong>{item.last_corro_date ? formatDate(item.last_corro_date) : 'Never'}</strong></div>
            <div>Days Overdue: <strong className="text-red-600">{item.days_since_corro || 'N/A'}</strong></div>
            <div>4-Week Count: <strong>{item.corro_count_4weeks}</strong></div>
            <div>Urgency: <strong className="text-red-600">{item.days_since_corro > 35 ? 'CRITICAL' : 'HIGH'}</strong></div>
          </div>
        </div>
      );
    
    case 'high_fatigue':
      return (
        <div className="space-y-3">
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <h4 className="font-medium text-red-800 text-sm mb-2">Fatigue Indicators</h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>Fatigue Score: <strong className="text-red-600">{item.compliance?.fatigue_score?.toFixed(1)}/100</strong></div>
              <div>Consecutive Nights: <strong>{item.compliance?.consecutive_night_shifts || 0}</strong></div>
              <div>Overtime Hours: <strong>{item.stats?.overtime_hours?.toFixed(1)}h</strong></div>
              <div>Recent Recalls: <strong>{item.stats?.recall_count || 0}</strong></div>
            </div>
          </div>
        </div>
      );
    
    default:
      return (
        <div className="text-sm text-slate-600">
          <p>Additional details available in full member profile view.</p>
        </div>
      );
  }
};

// Helper functions for urgency sorting and coloring
const getUrgencyLevel = (categoryType, count) => {
  if (count === 0) return 'ALL CLEAR';
  if (count > 10) return 'CRITICAL';
  if (count > 5) return 'HIGH';
  if (count > 2) return 'MODERATE';
  return 'LOW';
};

const getUrgencyColor = (categoryType, item, index) => {
  if (index < 3) return '#dc2626'; // Red for top 3 most urgent
  if (index < 6) return '#ea580c'; // Orange for next 3
  return '#0891b2'; // Blue for others
};

const getCategoryBadgeColor = (type) => {
  switch (type) {
    case 'high_fatigue': return 'bg-red-600';
    case 'eba_violations': return 'bg-red-700';
    case 'eba_warnings': return 'bg-orange-600';
    case 'eba_compliant': return 'bg-green-600';
    case 'over_76_hours': return 'bg-red-700';
    case 'approaching_76_hours': return 'bg-yellow-600';
    case 'night_recovery': return 'bg-purple-600';
    case 'rest_day_issues': return 'bg-indigo-600';
    case 'overdue_corro': return 'bg-orange-600';
    case 'leave_requests': return 'bg-green-600';
    case 'training_expiring': return 'bg-blue-600';
    case 'court_dates': return 'bg-purple-700';
    default: return 'bg-gray-600';
  }
};

const getCategoryBadgeText = (type, item) => {
  switch (type) {
    case 'high_fatigue': return 'HIGH FATIGUE';
    case 'eba_violations': return 'EBA VIOLATION';
    case 'eba_warnings': return 'EBA WARNING'; 
    case 'eba_compliant': return 'COMPLIANT';
    case 'over_76_hours': return 'OVER 76H';
    case 'approaching_76_hours': return 'APPROACHING 76H';
    case 'night_recovery': return 'NIGHT RECOVERY';
    case 'rest_day_issues': return 'REST DAY ISSUE';
    case 'overdue_corro': return 'OVERDUE CORRO';
    case 'leave_requests': return item?.request_type?.replace('_', ' ').toUpperCase() || 'LEAVE REQUEST';
    case 'training_expiring': return item?.days_remaining < 0 ? 'EXPIRED' : 'EXPIRING';
    case 'court_dates': return 'COURT DATE';
    default: return 'ISSUE';
  }
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('token');
      const storedUser = localStorage.getItem('user');
      
      if (storedToken && storedUser) {
        try {
          // Verify token is not expired
          const payload = JSON.parse(atob(storedToken.split('.')[1]));
          if (payload.exp > Date.now() / 1000) {
            setToken(storedToken);
            setUser(JSON.parse(storedUser));
            axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
          } else {
            // Token expired
            localStorage.removeItem('token');
            localStorage.removeItem('user');
          }
        } catch (error) {
          console.error('Invalid stored token:', error);
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      }
      setLoading(false);
    };
    
    initAuth();
  }, []);

  const login = async (vpNumber, password) => {
    try {
      console.log('Login attempt:', { vpNumber, password: password.substring(0, 3) + '***' });
      console.log('API URL:', `${API}/auth/login`);
      
      const requestData = {
        vp_number: vpNumber.toUpperCase(),
        password: password
      };
      
      console.log('Request data:', requestData);
      
      const response = await axios.post(`${API}/auth/login`, requestData);
      
      console.log('Full response:', response);
      console.log('Response status:', response.status);
      console.log('Response data:', response.data);
      
      // Check if response is successful
      if (response.status === 200 && response.data && response.data.access_token) {
        const { access_token, user: userData } = response.data;
        
        console.log('Login successful, setting user data:', userData);
        
        setToken(access_token);
        setUser(userData);
        localStorage.setItem('token', access_token);
        localStorage.setItem('user', JSON.stringify(userData));
        axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
        
        return true;
      } else {
        console.error('Unexpected response format:', response);
        return false;
      }
    } catch (error) {
      console.error('Login failed:', error);
      console.error('Login error response:', error.response?.data);
      console.error('Login error status:', error.response?.status);
      console.error('Login error headers:', error.response?.headers);
      console.error('Login error config:', error.config);
      return false;
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    delete axios.defaults.headers.common['Authorization'];
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Login Component
const Login = () => {
  const [vpNumber, setVpNumber] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login, user } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const success = await login(vpNumber, password);
    if (success) {
      // Redirect to dashboard after successful login
      navigate('/');
    } else {
      setError('Invalid credentials. Please try again.');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center p-4">
      {/* LOGIN STATUS INDICATOR */}
      {user && (
        <div className="absolute top-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg">
          ✅ Logged in as: {user.name} ({user.role})
        </div>
      )}
      
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-full mb-4">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">WATCHTOWER</h1>
          <p className="text-slate-300">Victoria Police Fatigue & Fairness Module</p>
        </div>

        <Card className="backdrop-blur-sm bg-white/10 border-white/20">
          <CardHeader className="text-center">
            <CardTitle className="text-white">Sign In</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="vpNumber" className="text-white">VP Number</Label>
                <Input
                  id="vpNumber"
                  type="text"
                  value={vpNumber}
                  onChange={(e) => setVpNumber(e.target.value)}
                  placeholder="VP12345"
                  className="bg-white/10 border-white/30 text-white placeholder:text-slate-400"
                  required
                />
              </div>
              <div>
                <Label htmlFor="password" className="text-white">Password</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  className="bg-white/10 border-white/30 text-white placeholder:text-slate-400"
                  required
                />
              </div>
              {error && (
                <div className="text-red-300 text-sm text-center bg-red-900/20 p-3 rounded border border-red-700/30">
                  {error}
                  <div className="mt-2 text-xs opacity-80">
                    💡 <strong>Troubleshooting:</strong>
                    <br />• Try the green "TEST LOGIN" button below
                    <br />• Press F12 → Console to see detailed logs
                    <br />• Ensure VP number is uppercase (VP12345)
                    <br />• Check for extra spaces in password field
                  </div>
                </div>
              )}
              <Button 
                type="submit" 
                className="w-full bg-blue-600 hover:bg-blue-700"
                disabled={loading}
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </Button>
            </form>
            
            {/* TEST LOGIN BUTTON - Remove this later */}
            <div className="mt-4 pt-4 border-t border-white/20">
              <Button 
                type="button"
                onClick={async () => {
                  setLoading(true);
                  setError('');
                  console.log('🧪 TEST LOGIN: Starting with hardcoded VP12345/password123');
                  const success = await login('VP12345', 'password123');
                  console.log('🧪 TEST LOGIN: Result =', success);
                  if (success) {
                    console.log('🧪 TEST LOGIN: Navigation to dashboard');
                    alert('✅ LOGIN SUCCESSFUL! You are now logged in as Sarah Connor (Inspector). The dashboard will load.');
                    navigate('/');
                  } else {
                    console.log('🧪 TEST LOGIN: Failed - check console logs above');
                    setError('Test login failed - check browser console (F12) for details');
                    alert('❌ LOGIN FAILED! Check the console for error details.');
                  }
                  setLoading(false);
                }}
                className="w-full bg-green-600 hover:bg-green-700 text-white font-medium"
                disabled={loading}
              >
                🧪 TEST LOGIN (VP12345) - INSTANT ACCESS
              </Button>
              
              {/* MANUAL TEST */}
              <Button 
                type="button"
                onClick={async () => {
                  setLoading(true);
                  setError('');
                  
                  const vpInput = document.querySelector('input[placeholder="VP12345"]');
                  const passInput = document.querySelector('input[placeholder="Enter password"]');
                  
                  const vpValue = vpInput?.value?.trim();
                  const passValue = passInput?.value?.trim();
                  
                  console.log('🔧 MANUAL TEST: VP =', vpValue, 'Password =', passValue?.substring(0, 3) + '***');
                  console.log('🔧 MANUAL TEST: API URL =', `${API}/auth/login`);
                  
                  if (!vpValue || !passValue) {
                    alert('❌ Please fill in both VP Number and Password fields first!');
                    setLoading(false);
                    return;
                  }
                  
                  const success = await login(vpValue, passValue);
                  
                  if (success) {
                    alert('✅ MANUAL LOGIN SUCCESSFUL! Dashboard will load now.');
                    navigate('/');
                  } else {
                    alert('❌ MANUAL LOGIN FAILED! Check credentials and try again.');
                    setError('Manual login failed with your entered credentials');
                  }
                  setLoading(false);
                }}
                className="w-full mt-2 bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs"
                disabled={loading}
              >
                🔧 TEST YOUR MANUAL INPUT
              </Button>
            </div>
            
            <div className="mt-6 text-center">
              <p className="text-slate-400 text-sm">Demo Credentials:</p>
              <p className="text-slate-300 text-xs">Inspector: VP12345 / password123</p>
              <p className="text-slate-300 text-xs">Sergeant: VP12346 / password123</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// Header Component
const Header = () => {
  const { user, logout } = useAuth();

  return (
    <header className="bg-slate-900 border-b border-slate-700 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Shield className="w-8 h-8 text-blue-400" />
            <div>
              <h1 className="text-xl font-bold text-white">WATCHTOWER</h1>
              <p className="text-xs text-slate-400">Fatigue & Fairness Module</p>
            </div>
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Avatar className="w-8 h-8">
              <AvatarFallback className="bg-blue-600 text-white text-sm">
                {user?.name?.split(' ').map(n => n[0]).join('') || 'U'}
              </AvatarFallback>
            </Avatar>
            <div className="text-right">
              <p className="text-sm font-medium text-white">{user?.name}</p>
              <p className="text-xs text-slate-400 capitalize">{user?.role?.replace('_', ' ')} • {user?.station}</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={logout} className="text-slate-400 hover:text-white">
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </header>
  );
};

// Workload Heatmap Component
const WorkloadHeatmap = ({ workloadData }) => {
  const getFatigueLevel = (stats) => {
    const fatigueScore = 
      (stats.van_shifts_pct * 0.3) + 
      (stats.watchhouse_shifts_pct * 0.3) + 
      (stats.night_shifts_pct * 0.2) + 
      (stats.overtime_hours * 0.1) + 
      (stats.recall_count * 0.1);
    
    if (fatigueScore > 60) return { level: 'high', color: 'bg-red-500', text: 'High Risk' };
    if (fatigueScore > 30) return { level: 'medium', color: 'bg-yellow-500', text: 'Moderate' };
    return { level: 'low', color: 'bg-green-500', text: 'Low Risk' };
  };

  const getComplianceStatus = (compliance) => {
    if (!compliance) return { color: 'bg-gray-500', text: 'Unknown' };
    
    switch (compliance.status) {
      case 'violation':
        return { color: 'bg-red-600', text: 'EBA Violation' };
      case 'warning':
        return { color: 'bg-orange-500', text: 'EBA Warning' };
      case 'compliant':
        return { color: 'bg-green-600', text: 'EBA Compliant' };
      default:
        return { color: 'bg-gray-500', text: 'Unknown' };
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
      {workloadData.map((member) => {
        const fatigue = getFatigueLevel(member.stats);
        const compliance = getComplianceStatus(member.compliance);
        
        return (
          <Card key={member.member_id} className="hover:shadow-lg transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">{member.member_name}</CardTitle>
                  <p className="text-sm text-slate-600">
                    {member.rank} • {member.seniority_years} years • {member.station}
                  </p>
                </div>
                <div className="flex flex-col space-y-1">
                  <Badge className={`${fatigue.color} text-white text-xs`}>
                    {fatigue.text}
                  </Badge>
                  <Badge className={`${compliance.color} text-white text-xs`}>
                    {compliance.text}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="flex items-center space-x-2">
                  <Car className="w-4 h-4 text-blue-500" />
                  <span>Van: {member.stats.van_shifts_pct}%</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Building className="w-4 h-4 text-purple-500" />
                  <span>Watchhouse: {member.stats.watchhouse_shifts_pct}%</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Moon className="w-4 h-4 text-indigo-500" />
                  <span>Night: {member.stats.night_shifts_pct}%</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Coffee className="w-4 h-4 text-green-500" />
                  <span>Corro: {member.stats.corro_shifts}</span>
                </div>
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Total Shifts (8 weeks)</span>
                  <span className="font-medium">{member.stats.total_shifts}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Fortnight Hours</span>
                  <span className={`font-medium ${member.compliance?.fortnight_hours > 65 ? 'text-orange-600' : member.compliance?.fortnight_hours > 76 ? 'text-red-600' : ''}`}>
                    {member.compliance?.fortnight_hours?.toFixed(1) || 0}h / 76h
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Overtime Hours</span>
                  <span className="font-medium">{member.stats.overtime_hours.toFixed(1)}h</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span>Recalls</span>
                  <span className="font-medium">{member.stats.recall_count}</span>
                </div>
              </div>

              {/* EBA Compliance Details */}
              {member.compliance && (member.compliance.violations?.length > 0 || member.compliance.warnings?.length > 0) && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <h4 className="font-medium text-red-800 text-sm mb-2">EBA Compliance Issues:</h4>
                  {member.compliance.violations?.map((violation, index) => (
                    <p key={index} className="text-xs text-red-700 mb-1">🚨 {violation}</p>
                  ))}
                  {member.compliance.warnings?.map((warning, index) => (
                    <p key={index} className="text-xs text-orange-700 mb-1">⚠️ {warning}</p>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
};

// EBA Compliance Dashboard Component
const ComplianceDashboard = ({ workloadData, onCategoryClick }) => {
  const complianceStats = workloadData.reduce((acc, member) => {
    if (!member.compliance) return acc;
    
    if (member.compliance.status === 'violation') {
      acc.violations++;
    } else if (member.compliance.status === 'warning') {
      acc.warnings++;
    } else {
      acc.compliant++;
    }
    
    if (member.compliance.fortnight_hours > 76) {
      acc.over76Hours++;
    } else if (member.compliance.fortnight_hours > 65) {
      acc.approaching76Hours++;
    }
    
    // Count night shift and rest day issues
    if (member.compliance.violations?.some(v => v.includes('consecutive night'))) {
      acc.nightShiftViolations++;
    }
    
    if (member.compliance.violations?.some(v => v.includes('rest days'))) {
      acc.restDayViolations++;
    }
    
    return acc;
  }, { 
    violations: 0, 
    warnings: 0, 
    compliant: 0, 
    over76Hours: 0, 
    approaching76Hours: 0,
    nightShiftViolations: 0,
    restDayViolations: 0
  });

  const violationMembers = workloadData.filter(m => m.compliance?.status === 'violation');
  const warningMembers = workloadData.filter(m => m.compliance?.status === 'warning');

  return (
    <div className="space-y-6">
      {/* Enhanced Clickable Compliance Stats Cards with Detailed Information */}
      <div className="grid grid-cols-1 md:grid-cols-7 gap-4">
        <Card 
          className="bg-red-50 border-red-200 cursor-pointer hover:shadow-lg transition-all duration-300 hover:bg-red-100"
          onClick={() => onCategoryClick('eba_violations', 'EBA Violations Detail')}
        >
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-red-600">{complianceStats.violations}</div>
            <div className="text-sm text-red-700 font-medium">EBA Violations</div>
            <div className="text-xs text-red-600 mt-1 opacity-75">Click for details</div>
            {complianceStats.violations > 0 && (
              <div className="mt-2 text-xs text-red-500">
                🚨 Immediate action required
              </div>
            )}
          </CardContent>
        </Card>
        
        <Card 
          className="bg-orange-50 border-orange-200 cursor-pointer hover:shadow-lg transition-all duration-300 hover:bg-orange-100"
          onClick={() => onCategoryClick('eba_warnings', 'EBA Warnings Detail')}
        >
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-orange-600">{complianceStats.warnings}</div>
            <div className="text-sm text-orange-700 font-medium">Warnings</div>
            <div className="text-xs text-orange-600 mt-1 opacity-75">Click for details</div>
            {complianceStats.warnings > 0 && (
              <div className="mt-2 text-xs text-orange-500">
                ⚠️ Monitor closely
              </div>
            )}
          </CardContent>
        </Card>
        
        <Card 
          className="bg-green-50 border-green-200 cursor-pointer hover:shadow-lg transition-all duration-300 hover:bg-green-100"
          onClick={() => onCategoryClick('eba_compliant', 'Compliant Members')}
        >
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-green-600">{complianceStats.compliant}</div>
            <div className="text-sm text-green-700 font-medium">Compliant</div>
            <div className="text-xs text-green-600 mt-1 opacity-75">Click for details</div>
            {complianceStats.compliant > 0 && (
              <div className="mt-2 text-xs text-green-500">
                ✅ All good
              </div>
            )}
          </CardContent>
        </Card>
        
        <Card 
          className="bg-red-50 border-red-200 cursor-pointer hover:shadow-lg transition-all duration-300 hover:bg-red-100"
          onClick={() => onCategoryClick('over_76_hours', 'Members Over 76 Hours')}
        >
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-red-600">{complianceStats.over76Hours}</div>
            <div className="text-sm text-red-700 font-medium">Over 76h</div>
            <div className="text-xs text-red-600 mt-1 opacity-75">Click for details</div>
            {complianceStats.over76Hours > 0 && (
              <div className="mt-2 text-xs text-red-500">
                ⏰ EBA breach
              </div>
            )}
          </CardContent>
        </Card>
        
        <Card 
          className="bg-yellow-50 border-yellow-200 cursor-pointer hover:shadow-lg transition-all duration-300 hover:bg-yellow-100"
          onClick={() => onCategoryClick('approaching_76_hours', 'Members Approaching 76 Hours')}
        >
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-yellow-600">{complianceStats.approaching76Hours}</div>
            <div className="text-sm text-yellow-700 font-medium">Approaching 76h</div>
            <div className="text-xs text-yellow-600 mt-1 opacity-75">Click for details</div>
            {complianceStats.approaching76Hours > 0 && (
              <div className="mt-2 text-xs text-yellow-500">
                ⚠️ Monitor hours
              </div>
            )}
          </CardContent>
        </Card>
        
        <Card 
          className="bg-purple-50 border-purple-200 cursor-pointer hover:shadow-lg transition-all duration-300 hover:bg-purple-100"
          onClick={() => onCategoryClick('night_recovery', 'Night Recovery Issues')}
        >
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-purple-600">{complianceStats.nightShiftViolations}</div>
            <div className="text-sm text-purple-700 font-medium">Night Recovery</div>
            <div className="text-xs text-purple-600 mt-1 opacity-75">Click for details</div>
            {complianceStats.nightShiftViolations > 0 && (
              <div className="mt-2 text-xs text-purple-500">
                🌙 Recovery needed
              </div>
            )}
          </CardContent>
        </Card>
        
        <Card 
          className="bg-indigo-50 border-indigo-200 cursor-pointer hover:shadow-lg transition-all duration-300 hover:bg-indigo-100"
          onClick={() => onCategoryClick('rest_day_issues', 'Rest Day Issues')}
        >
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-indigo-600">{complianceStats.restDayViolations}</div>
            <div className="text-sm text-indigo-700 font-medium">Rest Day Issues</div>
            <div className="text-xs text-indigo-600 mt-1 opacity-75">Click for details</div>
            {complianceStats.restDayViolations > 0 && (
              <div className="mt-2 text-xs text-indigo-500">
                📅 Insufficient rest
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Sprint 2 Features: Night Shift Recovery Alerts */}
      {violationMembers.some(m => m.compliance?.violations?.some(v => v.includes('consecutive night'))) && (
        <Card className="border-purple-200 bg-purple-50">
          <CardHeader>
            <CardTitle className="text-purple-800 flex items-center space-x-2">
              <Moon className="w-5 h-5" />
              <span>Night Shift Recovery Violations - Immediate Action Required</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {violationMembers
                .filter(m => m.compliance?.violations?.some(v => v.includes('consecutive night')))
                .map((member) => (
                <div key={member.member_id} className="bg-white p-4 rounded-lg border border-purple-200">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-medium text-purple-800">{member.member_name}</h4>
                      <p className="text-sm text-purple-600">{member.rank} • {member.station}</p>
                    </div>
                    <Badge className="bg-purple-600 text-white">NIGHT RECOVERY NEEDED</Badge>
                  </div>
                  <div className="mt-3 space-y-1">
                    {member.compliance?.violations?.filter(v => v.includes('consecutive night')).map((violation, index) => (
                      <p key={index} className="text-sm text-purple-700">🌙 {violation}</p>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Rest Day Compliance Alerts */}
      {violationMembers.some(m => m.compliance?.violations?.some(v => v.includes('rest days'))) && (
        <Card className="border-indigo-200 bg-indigo-50">
          <CardHeader>
            <CardTitle className="text-indigo-800 flex items-center space-x-2">
              <Calendar className="w-5 h-5" />
              <span>Rest Day Compliance Violations</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {violationMembers
                .filter(m => m.compliance?.violations?.some(v => v.includes('rest days')))
                .map((member) => (
                <div key={member.member_id} className="bg-white p-4 rounded-lg border border-indigo-200">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-medium text-indigo-800">{member.member_name}</h4>
                      <p className="text-sm text-indigo-600">{member.rank} • {member.station}</p>
                    </div>
                    <Badge className="bg-indigo-600 text-white">INSUFFICIENT REST</Badge>
                  </div>
                  <div className="mt-3 space-y-1">
                    {member.compliance?.violations?.filter(v => v.includes('rest days')).map((violation, index) => (
                      <p key={index} className="text-sm text-indigo-700">📅 {violation}</p>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Existing violations section remains the same... */}
      {violationMembers.length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-red-800 flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5" />
              <span>EBA Violations Require Immediate Action ({violationMembers.length})</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {violationMembers.map((member) => (
                <div key={member.member_id} className="bg-white p-4 rounded-lg border border-red-200">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-medium text-red-800">{member.member_name}</h4>
                      <p className="text-sm text-red-600">{member.rank} • {member.station}</p>
                      <p className="text-sm font-medium text-red-700">
                        Current Fortnight: {member.compliance?.fortnight_hours?.toFixed(1)}h / 76h
                      </p>
                    </div>
                    <Badge className="bg-red-600 text-white">VIOLATION</Badge>
                  </div>
                  <div className="mt-3 space-y-1">
                    {member.compliance?.violations?.map((violation, index) => (
                      <p key={index} className="text-sm text-red-700">
                        {violation.includes('consecutive night') ? '🌙' : 
                         violation.includes('rest days') ? '📅' :
                         violation.includes('60h in 7 days') ? '⏰' : '🚨'} {violation}
                      </p>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Warnings */}
      {warningMembers.length > 0 && (
        <Card className="border-orange-200 bg-orange-50">
          <CardHeader>
            <CardTitle className="text-orange-800 flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5" />
              <span>EBA Warnings - Monitor Closely ({warningMembers.length})</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {warningMembers.map((member) => (
                <div key={member.member_id} className="bg-white p-4 rounded-lg border border-orange-200">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-medium text-orange-800">{member.member_name}</h4>
                      <p className="text-sm text-orange-600">{member.rank} • {member.station}</p>
                      <p className="text-sm font-medium text-orange-700">
                        Current Fortnight: {member.compliance?.fortnight_hours?.toFixed(1)}h / 76h
                      </p>
                    </div>
                    <Badge className="bg-orange-500 text-white">WARNING</Badge>
                  </div>
                  <div className="mt-3 space-y-1">
                    {member.compliance?.warnings?.map((warning, index) => (
                      <p key={index} className="text-sm text-orange-700">⚠️ {warning}</p>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* All Members Compliance Status */}
      <Card>
        <CardHeader>
          <CardTitle>All Members - EBA Compliance Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {workloadData.map((member) => {
              const statusColor = member.compliance?.status === 'violation' ? 'text-red-600' :
                                 member.compliance?.status === 'warning' ? 'text-orange-600' : 'text-green-600';
              const statusBg = member.compliance?.status === 'violation' ? 'bg-red-100' :
                              member.compliance?.status === 'warning' ? 'bg-orange-100' : 'bg-green-100';
              
              return (
                <div key={member.member_id} className={`flex items-center justify-between p-3 ${statusBg} rounded-lg`}>
                  <div>
                    <p className="font-medium">{member.member_name}</p>
                    <p className="text-sm text-slate-600">{member.rank} • {member.station}</p>
                  </div>
                  <div className="text-right">
                    <p className={`font-medium ${statusColor} capitalize`}>
                      {member.compliance?.status || 'Unknown'}
                    </p>
                    <p className="text-sm text-slate-600">
                      {member.compliance?.fortnight_hours?.toFixed(1) || 0}h / 76h
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Corro Distribution Component
const CorroDistribution = ({ corroData }) => {
  const overdueMembers = corroData.filter(m => m.overdue);
  
  return (
    <div className="space-y-6">
      {overdueMembers.length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-red-800 flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5" />
              <span>Overdue Corro Assignments ({overdueMembers.length})</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {overdueMembers.map((member) => (
                <div key={member.member_id} className="bg-white p-3 rounded-lg border">
                  <p className="font-medium text-red-800">{member.member_name}</p>
                  <p className="text-sm text-red-600">{member.station}</p>
                  <p className="text-xs text-red-500">
                    {member.days_since_corro ? `${member.days_since_corro} days ago` : 'Never assigned'}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
      
      <Card>
        <CardHeader>
          <CardTitle>Corro Distribution (Last 4 Weeks)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {corroData.map((member) => (
              <div key={member.member_id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                <div>
                  <p className="font-medium">{member.member_name}</p>
                  <p className="text-sm text-slate-600">{member.station}</p>
                </div>
                <div className="text-right">
                  <p className="font-medium">{member.corro_count_4weeks} shifts</p>
                  <p className="text-sm text-slate-600">
                    {member.days_since_corro ? `${member.days_since_corro}d ago` : 'Never'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Member Preferences Dialog - No X button, just Cancel
const MemberPreferencesDialog = ({ member, isOpen, onClose, onUpdate }) => {
  const [preferences, setPreferences] = useState(member?.preferences || {});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (member?.preferences) {
      setPreferences(member.preferences);
    }
  }, [member]);

  const handleUpdate = async () => {
    setLoading(true);
    try {
      await axios.put(`${API}/members/${member.id}/preferences`, preferences);
      onUpdate();
      onClose();
    } catch (error) {
      console.error('Failed to update preferences:', error);
    }
    setLoading(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-6">
          <h2 className="text-2xl font-bold">Member Preferences</h2>
          <p className="text-blue-100 mt-1">{member?.name} • {member?.rank} • {member?.station}</p>
        </div>
        
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-6">
              <div>
                <Label className="text-base font-semibold text-slate-700">Night Shift Tolerance</Label>
                <p className="text-sm text-slate-500 mb-3">Maximum night shifts per month</p>
                <Select 
                  value={preferences.night_shift_tolerance?.toString() || "2"}
                  onValueChange={(value) => setPreferences({...preferences, night_shift_tolerance: parseInt(value)})}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0">0 shifts (No nights)</SelectItem>
                    <SelectItem value="2">2 shifts (Minimal)</SelectItem>
                    <SelectItem value="4">4 shifts (Standard)</SelectItem>
                    <SelectItem value="6">6 shifts (Above average)</SelectItem>
                    <SelectItem value="8">8+ shifts (High tolerance)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center space-x-3 p-3 bg-slate-50 rounded-lg">
                  <Switch 
                    checked={preferences.recall_willingness ?? true}
                    onCheckedChange={(checked) => setPreferences({...preferences, recall_willingness: checked})}
                  />
                  <div>
                    <Label className="text-base font-medium">Out-of-hours Recall</Label>
                    <p className="text-sm text-slate-500">Willing to be contacted for emergency recalls</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3 p-3 bg-slate-50 rounded-lg">
                  <Switch 
                    checked={preferences.avoid_consecutive_doubles ?? true}
                    onCheckedChange={(checked) => setPreferences({...preferences, avoid_consecutive_doubles: checked})}
                  />
                  <div>
                    <Label className="text-base font-medium">Avoid Consecutive Doubles</Label>
                    <p className="text-sm text-slate-500">Prevent back-to-back double shifts when possible</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3 p-3 bg-slate-50 rounded-lg">
                  <Switch 
                    checked={preferences.avoid_four_earlies ?? true}
                    onCheckedChange={(checked) => setPreferences({...preferences, avoid_four_earlies: checked})}
                  />
                  <div>
                    <Label className="text-base font-medium">Limit Early Shifts</Label>
                    <p className="text-sm text-slate-500">Avoid 4+ consecutive early shifts</p>
                  </div>
                </div>
              </div>

              <div>
                <Label className="text-base font-semibold text-slate-700">Preferred Rest Days</Label>
                <p className="text-sm text-slate-500 mb-3">Select preferred days off when possible</p>
                <div className="grid grid-cols-2 gap-2">
                  {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map(day => (
                    <div key={day} className="flex items-center space-x-2">
                      <Switch 
                        checked={preferences.preferred_rest_days?.includes(day) || false}
                        onCheckedChange={(checked) => {
                          const currentDays = preferences.preferred_rest_days || [];
                          if (checked) {
                            setPreferences({...preferences, preferred_rest_days: [...currentDays, day]});
                          } else {
                            setPreferences({...preferences, preferred_rest_days: currentDays.filter(d => d !== day)});
                          }
                        }}
                      />
                      <Label className="text-sm">{day}</Label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="space-y-6">
              <div>
                <Label className="text-base font-semibold text-slate-700">Medical Limitations</Label>
                <p className="text-sm text-slate-500 mb-3">Any medical considerations for shift assignments</p>
                <Textarea 
                  value={preferences.medical_limitations || ''}
                  onChange={(e) => setPreferences({...preferences, medical_limitations: e.target.value})}
                  placeholder="e.g., Lower back issues, requires ergonomic equipment..."
                  className="min-h-[100px] resize-none"
                />
              </div>
              
              <div>
                <Label className="text-base font-semibold text-slate-700">Welfare Notes</Label>
                <p className="text-sm text-slate-500 mb-3">Additional welfare considerations or personal circumstances</p>
                <Textarea 
                  value={preferences.welfare_notes || ''}
                  onChange={(e) => setPreferences({...preferences, welfare_notes: e.target.value})}
                  placeholder="e.g., Recently returned from extended leave, family commitments..."
                  className="min-h-[100px] resize-none"
                />
              </div>

              <div>
                <Label className="text-base font-semibold text-slate-700">Emergency Contact</Label>
                <p className="text-sm text-slate-500 mb-3">Contact for emergency situations</p>
                <Input 
                  value={preferences.emergency_contact || ''}
                  onChange={(e) => setPreferences({...preferences, emergency_contact: e.target.value})}
                  placeholder="e.g., spouse_name@email.com or +61 4XX XXX XXX"
                />
              </div>
            </div>
          </div>
        </div>
        
        <div className="bg-slate-50 px-6 py-4 flex justify-end space-x-3 border-t">
          <Button 
            variant="outline" 
            onClick={onClose}
            className="px-6"
          >
            Cancel
          </Button>
          <Button 
            onClick={handleUpdate} 
            disabled={loading}
            className="px-6 bg-blue-600 hover:bg-blue-700 text-white"
          >
            {loading ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Updating...</span>
              </div>
            ) : 'Update Preferences'}
          </Button>
        </div>
      </div>
    </div>
  );
};

// Main Dashboard Component
const Dashboard = () => {
  const [workloadData, setWorkloadData] = useState([]);
  const [corroData, setCorroData] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMember, setSelectedMember] = useState(null);
  const [categoryModal, setCategoryModal] = useState({ isOpen: false, category: null });
  const [detailedMemberView, setDetailedMemberView] = useState({ isOpen: false, member: null });
  const { user } = useAuth();

  const fetchData = async () => {
    try {
      const [workloadRes, corroRes, membersRes] = await Promise.all([
        axios.get(`${API}/analytics/workload-summary`),
        axios.get(`${API}/analytics/corro-distribution`),
        axios.get(`${API}/members`)
      ]);
      
      setWorkloadData(workloadRes.data);
      setCorroData(corroRes.data);
      setMembers(membersRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const initializeSampleData = async () => {
    try {
      await axios.post(`${API}/init-sample-data`);
      await fetchData();
    } catch (error) {
      console.error('Failed to initialize sample data:', error);
    }
  };

  const openCategoryModal = (type, title) => {
    setCategoryModal({
      isOpen: true,
      category: { type, title }
    });
  };

  const closeCategoryModal = () => {
    setCategoryModal({ isOpen: false, category: null });
  };

  const openDetailedMemberView = (member) => {
    setDetailedMemberView({ isOpen: true, member });
  };

  const closeDetailedMemberView = () => {
    setDetailedMemberView({ isOpen: false, member: null });
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  const highRiskMembers = workloadData.filter(m => {
    const fatigueScore = 
      (m.stats.van_shifts_pct * 0.3) + 
      (m.stats.watchhouse_shifts_pct * 0.3) + 
      (m.stats.night_shifts_pct * 0.2) + 
      (m.stats.overtime_hours * 0.1) + 
      (m.stats.recall_count * 0.1);
    return fatigueScore > 60;
  }).length;

  const overdueCorroCount = corroData.filter(m => m.overdue).length;
  
  const complianceViolations = workloadData.filter(m => m.compliance?.status === 'violation').length;
  const nightRecoveryNeeded = workloadData.filter(m => 
    m.compliance?.violations?.some(v => v.includes('consecutive night'))
  ).length;
  const restDayIssues = workloadData.filter(m => 
    m.compliance?.violations?.some(v => v.includes('rest days'))
  ).length;

  return (
    <div className="min-h-screen bg-slate-50">
      <Header />
      
      <div className="p-6">
        {workloadData.length === 0 && (
          <Card className="mb-6 border-blue-200 bg-blue-50">
            <CardContent className="p-6 text-center">
              <h3 className="text-lg font-semibold text-blue-800 mb-2">Welcome to WATCHTOWER</h3>
              <p className="text-blue-700 mb-4">
                No data found. Would you like to initialize with sample data to explore the system?
              </p>
              <Button onClick={initializeSampleData} className="bg-blue-600 hover:bg-blue-700">
                Initialize Sample Data
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Quick Stats - Clickable */}
        <div className="grid grid-cols-1 md:grid-cols-7 gap-4 mb-8">
          <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => openCategoryModal('members', 'Active Members')}>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <Users className="w-6 h-6 text-blue-600" />
                <div>
                  <p className="text-xl font-bold">{workloadData.length}</p>
                  <p className="text-xs text-slate-600">Active Members</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => openCategoryModal('high_fatigue', 'High Fatigue Risk Members')}>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-6 h-6 text-red-600" />
                <div>
                  <p className="text-xl font-bold text-red-600">{highRiskMembers}</p>
                  <p className="text-xs text-slate-600">High Fatigue Risk</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => openCategoryModal('eba_violations', 'EBA Violations Detail')}>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <Shield className="w-6 h-6 text-red-600" />
                <div>
                  <p className="text-xl font-bold text-red-600">{complianceViolations}</p>
                  <p className="text-xs text-slate-600">EBA Violations</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => openCategoryModal('night_recovery', 'Night Recovery Issues')}>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <Moon className="w-6 h-6 text-purple-600" />
                <div>
                  <p className="text-xl font-bold text-purple-600">{nightRecoveryNeeded}</p>
                  <p className="text-xs text-slate-600">Night Recovery</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => openCategoryModal('rest_day_issues', 'Rest Day Issues')}>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <Calendar className="w-6 h-6 text-indigo-600" />
                <div>
                  <p className="text-xl font-bold text-indigo-600">{restDayIssues}</p>
                  <p className="text-xs text-slate-600">Rest Day Issues</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => openCategoryModal('overdue_corro', 'Overdue Corro Assignments')}>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <Coffee className="w-6 h-6 text-orange-600" />
                <div>
                  <p className="text-xl font-bold text-orange-600">{overdueCorroCount}</p>
                  <p className="text-xs text-slate-600">Overdue Corro</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <TrendingUp className="w-6 h-6 text-green-600" />
                <div>
                  <p className="text-xl font-bold">8</p>
                  <p className="text-xs text-slate-600">Weeks Tracked</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <Tabs defaultValue="workload" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="workload" className="flex items-center space-x-2">
              <BarChart3 className="w-4 h-4" />
              <span>Workload Heatmap</span>
            </TabsTrigger>
            <TabsTrigger value="compliance" className="flex items-center space-x-2">
              <Shield className="w-4 h-4" />
              <span>EBA Compliance</span>
            </TabsTrigger>
            <TabsTrigger value="corro" className="flex items-center space-x-2">
              <Coffee className="w-4 h-4" />
              <span>Corro Distribution</span>
            </TabsTrigger>
            <TabsTrigger value="roster" className="flex items-center space-x-2">
              <Calendar className="w-4 h-4" />
              <span>Roster Producer</span>
            </TabsTrigger>
            <TabsTrigger value="members" className="flex items-center space-x-2">
              <Users className="w-4 h-4" />
              <span>Member Profiles</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="workload">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <BarChart3 className="w-5 h-5" />
                  <span>Shift Load Heatmap (Last 8 Weeks)</span>
                </CardTitle>
                <p className="text-slate-600">
                  Visual overview of member workloads highlighting fatigue risks, shift distribution inequities, and EBA compliance status
                </p>
              </CardHeader>
              <CardContent>
                <WorkloadHeatmap workloadData={workloadData} />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="compliance">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Shield className="w-5 h-5" />
                  <span>EBA Compliance Dashboard</span>
                </CardTitle>
                <p className="text-slate-600">
                  Monitor Enterprise Bargaining Agreement compliance including 76-hour fortnight limits and minimum break requirements
                </p>
              </CardHeader>
              <CardContent>
                <ComplianceDashboard workloadData={workloadData} onCategoryClick={openCategoryModal} />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="corro">
            <CorroDistribution corroData={corroData} />
          </TabsContent>

          <TabsContent value="roster">
            <RosterProducer user={user} />
          </TabsContent>

          <TabsContent value="members">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Users className="w-5 h-5" />
                  <span>Member Profiles & Preferences</span>
                </CardTitle>
                <p className="text-slate-600">
                  Manage member preferences and view detailed profiles for informed rostering decisions
                </p>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {members.map((member) => (
                    <Card key={member.id} className="hover:shadow-lg transition-shadow">
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h3 className="font-semibold">{member.name}</h3>
                            <p className="text-sm text-slate-600">
                              {member.rank} • {member.seniority_years} years
                            </p>
                            <Badge variant="outline" className="mt-1 text-xs">
                              {member.station}
                            </Badge>
                          </div>
                        </div>
                        
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span>Night shifts/month:</span>
                            <span className="font-medium">{member.preferences?.night_shift_tolerance || 2}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Recall willing:</span>
                            <span className={member.preferences?.recall_willingness ? "text-green-600" : "text-red-600"}>
                              {member.preferences?.recall_willingness ? "Yes" : "No"}
                            </span>
                          </div>
                          {member.preferences?.medical_limitations && (
                            <div className="pt-2 border-t">
                              <p className="text-xs text-slate-600">Medical: {member.preferences.medical_limitations}</p>
                            </div>
                          )}
                          {member.preferences?.welfare_notes && (
                            <div className="pt-2 border-t">
                              <p className="text-xs text-slate-600">Notes: {member.preferences.welfare_notes}</p>
                            </div>
                          )}
                        </div>
                        
                        {/* Action Buttons */}
                        <div className="mt-4 pt-4 border-t border-slate-200 flex space-x-2">
                          <Button 
                            size="sm" 
                            variant="outline"
                            onClick={() => openDetailedMemberView(member)}
                            className="flex-1"
                          >
                            <Eye className="w-3 h-3 mr-1" />
                            View Details
                          </Button>
                          {(user?.role === 'sergeant' || user?.role === 'inspector' || user?.role === 'admin') && (
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => setSelectedMember(member)}
                            >
                              <Settings className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Category Detail Modal */}
        <CategoryDetailModal 
          category={categoryModal.category}
          isOpen={categoryModal.isOpen}
          onClose={closeCategoryModal}
        />

        {/* Detailed Member View Modal */}
        <DetailedMemberView 
          member={detailedMemberView.member}
          isOpen={detailedMemberView.isOpen}
          onClose={closeDetailedMemberView}
        />

        {/* Member Preferences Dialog */}
        {selectedMember && (
          <MemberPreferencesDialog 
            member={selectedMember}
            isOpen={!!selectedMember}
            onClose={() => setSelectedMember(null)}
            onUpdate={fetchData}
          />
        )}
      </div>
    </div>
  );
};

// Detailed Member View Component
const DetailedMemberView = ({ member, isOpen, onClose }) => {
  const [memberDetails, setMemberDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (isOpen && member?.id) {
      fetchMemberDetails();
    }
  }, [isOpen, member]);

  const fetchMemberDetails = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/members/${member.id}/detailed-view`);
      setMemberDetails(response.data);
    } catch (error) {
      console.error('Failed to fetch member details:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl max-w-7xl w-full max-h-[95vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center">
                <User className="w-8 h-8 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold">{member?.name}</h2>
                <p className="text-blue-100">
                  {member?.rank} • {member?.station} • {member?.seniority_years} years service
                </p>
                <p className="text-blue-200 text-sm">VP{member?.vp_number}</p>
              </div>
            </div>
            <Button 
              onClick={onClose} 
              variant="outline" 
              className="bg-white/10 border-white/30 text-white hover:bg-white/20"
            >
              Close
            </Button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-slate-200">
          <div className="flex overflow-x-auto">
            {[
              { id: 'overview', label: 'Overview', icon: User },
              { id: 'shifts', label: 'Shift Breakdown', icon: BarChart3 },
              { id: 'compliance', label: 'EBA Compliance', icon: Shield },
              { id: 'preferences', label: 'Preferences', icon: Settings },
              { id: 'activity', label: 'Activity Log', icon: History },
              { id: 'fatigue', label: 'Fatigue Risk', icon: Activity },
              { id: 'schedule', label: 'Schedule History', icon: Calendar },
              { id: 'equity', label: 'Equity Tracking', icon: Scale }
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 px-6 py-4 border-b-2 whitespace-nowrap font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600 bg-blue-50'
                      : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(95vh-200px)]">
          {loading ? (
            <div className="flex justify-center items-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <span className="ml-4 text-slate-600">Loading member details...</span>
            </div>
          ) : (
            <div className="p-6">
              {activeTab === 'overview' && memberDetails && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Member Info Card */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <User className="w-5 h-5 text-blue-600" />
                        <span>Member Information</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex justify-between">
                        <span className="text-slate-600">Rank:</span>
                        <span className="font-medium">{memberDetails.member_info.rank}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-600">Station:</span>
                        <span className="font-medium">{memberDetails.member_info.station}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-600">Seniority:</span>
                        <span className="font-medium">{memberDetails.member_info.seniority_years} years</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-600">VP Number:</span>
                        <span className="font-medium">VP{memberDetails.member_info.vp_number}</span>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Quick Stats */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <BarChart3 className="w-5 h-5 text-green-600" />
                        <span>Quick Stats (12 weeks)</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex justify-between">
                        <span className="text-slate-600">Total Shifts:</span>
                        <span className="font-medium">{memberDetails.shift_breakdown.total_shifts}</span>
                      </div>
                      <div className="flex justify-between">  
                        <span className="text-slate-600">Current Status:</span>
                        <Badge className={
                          memberDetails.eba_compliance_history.current_status === 'violation' ? 'bg-red-600' :
                          memberDetails.eba_compliance_history.current_status === 'warning' ? 'bg-orange-500' : 'bg-green-600'
                        }>
                          {memberDetails.eba_compliance_history.current_status?.toUpperCase()}
                        </Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-600">Fortnight Hours:</span>
                        <span className={`font-medium ${
                          memberDetails.eba_compliance_history.fortnight_hours > 76 ? 'text-red-600' :
                          memberDetails.eba_compliance_history.fortnight_hours > 65 ? 'text-orange-600' : ''
                        }`}>
                          {memberDetails.eba_compliance_history.fortnight_hours?.toFixed(1)}h / 76h
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-600">Fairness Score:</span>
                        <span className="font-medium">{memberDetails.equity_tracking.fairness_score}/100</span>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Risk Assessment */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <Activity className="w-5 h-5 text-red-600" />
                        <span>Risk Assessment</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex justify-between">
                        <span className="text-slate-600">Fatigue Risk:</span>
                        <Badge className={
                          memberDetails.fatigue_risk_projection.projected_risk === 'high' ? 'bg-red-600' :
                          memberDetails.fatigue_risk_projection.projected_risk === 'medium' ? 'bg-orange-500' : 'bg-green-600'
                        }>
                          {memberDetails.fatigue_risk_projection.projected_risk?.toUpperCase()}
                        </Badge>
                      </div>
                      {memberDetails.fatigue_risk_projection.risk_factors.length > 0 && (
                        <div>
                          <p className="text-slate-600 text-sm mb-2">Risk Factors:</p>
                          {memberDetails.fatigue_risk_projection.risk_factors.map((factor, index) => (
                            <p key={index} className="text-xs text-red-600 mb-1">• {factor}</p>
                          ))}
                        </div>
                      )}
                      {memberDetails.fatigue_risk_projection.recommendations.length > 0 && (
                        <div>
                          <p className="text-slate-600 text-sm mb-2">Recommendations:</p>
                          {memberDetails.fatigue_risk_projection.recommendations.map((rec, index) => (
                            <p key={index} className="text-xs text-blue-600 mb-1">• {rec}</p>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              )}

              {activeTab === 'shifts' && memberDetails && (
                <div className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>Shift Type Distribution (Last 12 weeks)</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {Object.entries(memberDetails.shift_breakdown.shift_types).map(([type, count]) => (
                          <div key={type} className="text-center p-4 bg-slate-50 rounded-lg">
                            <p className="text-2xl font-bold text-blue-600">{count}</p>
                            <p className="text-sm text-slate-600 capitalize">{type.replace('_', ' ')} Shifts</p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Weekly Hours Trend</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {memberDetails.shift_breakdown.weekly_hours.slice(0, 8).map((week, index) => (
                          <div key={index} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                            <span className="text-sm font-medium">
                              Week {formatDate(week.week_start)}
                            </span>
                            <div className="flex items-center space-x-4">
                              <span className="text-sm text-slate-600">{week.shifts} shifts</span>
                              <span className={`font-medium ${
                                week.hours > 40 ? 'text-red-600' : week.hours > 35 ? 'text-orange-600' : 'text-green-600'
                              }`}>
                                {week.hours}h
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              {activeTab === 'compliance' && memberDetails && (
                <div className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <Shield className="w-5 h-5" />
                        <span>EBA Compliance Status</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <h4 className="font-semibold mb-3">Current Status</h4>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span>Status:</span>
                              <Badge className={
                                memberDetails.eba_compliance_history.current_status === 'violation' ? 'bg-red-600' :
                                memberDetails.eba_compliance_history.current_status === 'warning' ? 'bg-orange-500' : 'bg-green-600'
                              }>
                                {memberDetails.eba_compliance_history.current_status?.toUpperCase()}
                              </Badge>
                            </div>
                            <div className="flex justify-between">
                              <span>Fortnight Hours:</span>
                              <span className={
                                memberDetails.eba_compliance_history.fortnight_hours > 76 ? 'text-red-600 font-medium' : ''
                              }>
                                {memberDetails.eba_compliance_history.fortnight_hours?.toFixed(1)}h / 76h
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Trend:</span>
                              <span className="capitalize">{memberDetails.eba_compliance_history.compliance_trend}</span>
                            </div>
                          </div>
                        </div>
                        
                        <div>
                          <h4 className="font-semibold mb-3">Issues</h4>
                          {memberDetails.eba_compliance_history.violations?.length > 0 && (
                            <div className="mb-4">
                              <p className="text-red-600 font-medium text-sm mb-2">Violations ({memberDetails.eba_compliance_history.violations.length})</p>
                              {memberDetails.eba_compliance_history.violations.map((violation, index) => (
                                <p key={index} className="text-xs text-red-600 mb-1">• {violation}</p>
                              ))}
                            </div>
                          )}
                          {memberDetails.eba_compliance_history.warnings?.length > 0 && (
                            <div>
                              <p className="text-orange-600 font-medium text-sm mb-2">Warnings ({memberDetails.eba_compliance_history.warnings.length})</p>
                              {memberDetails.eba_compliance_history.warnings.map((warning, index) => (
                                <p key={index} className="text-xs text-orange-600 mb-1">• {warning}</p>
                              ))}
                            </div>
                          )}
                          {(!memberDetails.eba_compliance_history.violations || memberDetails.eba_compliance_history.violations.length === 0) &&
                           (!memberDetails.eba_compliance_history.warnings || memberDetails.eba_compliance_history.warnings.length === 0) && (
                            <p className="text-green-600 text-sm">✅ No current compliance issues</p>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              {activeTab === 'preferences' && memberDetails && (
                <Card>
                  <CardHeader>
                    <CardTitle>Member Preferences</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <h4 className="font-semibold mb-3">Shift Preferences</h4>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span>Night Shift Tolerance:</span>
                            <span className="font-medium">{memberDetails.member_preferences.night_shift_tolerance || 2} shifts/month</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Recall Willingness:</span>
                            <span className={memberDetails.member_preferences.recall_willingness ? "text-green-600" : "text-red-600"}>
                              {memberDetails.member_preferences.recall_willingness ? "Yes" : "No"}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>Avoid Consecutive Doubles:</span>
                            <span className={memberDetails.member_preferences.avoid_consecutive_doubles ? "text-green-600" : "text-red-600"}>
                              {memberDetails.member_preferences.avoid_consecutive_doubles ? "Yes" : "No"}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div>
                        <h4 className="font-semibold mb-3">Other Preferences</h4>
                        {memberDetails.member_preferences.preferred_rest_days?.length > 0 && (
                          <div className="mb-3">
                            <p className="text-sm text-slate-600 mb-1">Preferred Rest Days:</p>
                            <div className="flex flex-wrap gap-1">
                              {memberDetails.member_preferences.preferred_rest_days.map(day => (
                                <Badge key={day} variant="outline" className="text-xs">{day}</Badge>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {memberDetails.member_preferences.medical_limitations && (
                          <div className="mb-3">
                            <p className="text-sm text-slate-600 mb-1">Medical Limitations:</p>
                            <p className="text-xs text-slate-700 bg-slate-50 p-2 rounded">
                              {memberDetails.member_preferences.medical_limitations}
                            </p>
                          </div>
                        )}
                        
                        {memberDetails.member_preferences.welfare_notes && (
                          <div>
                            <p className="text-sm text-slate-600 mb-1">Welfare Notes:</p>
                            <p className="text-xs text-slate-700 bg-slate-50 p-2 rounded">
                              {memberDetails.member_preferences.welfare_notes}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {activeTab === 'activity' && memberDetails && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <History className="w-5 h-5" />
                      <span>Recent Activity Log</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {memberDetails.activity_log.map((activity, index) => (
                        <div key={index} className="flex items-start space-x-3 p-3 bg-slate-50 rounded-lg">
                          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                            <FileText className="w-4 h-4 text-blue-600" />
                          </div>
                          <div className="flex-1">
                            <div className="flex justify-between items-start">
                              <div>
                                <p className="font-medium text-sm">{activity.action}</p>
                                <p className="text-xs text-slate-600">{activity.details}</p>
                              </div>
                              <div className="text-right">
                                <p className="text-xs text-slate-500">{formatDateTime(activity.date)}</p>
                                <p className="text-xs text-slate-400">by {activity.performed_by}</p>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {activeTab === 'fatigue' && memberDetails && (
                <div className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <Activity className="w-5 h-5 text-red-600" />
                        <span>Fatigue Risk Analysis</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <h4 className="font-semibold mb-3">Current Assessment</h4>
                          <div className="space-y-3">
                            <div className="flex justify-between">
                              <span>Risk Level:</span>
                              <Badge className={
                                memberDetails.fatigue_risk_projection.projected_risk === 'high' ? 'bg-red-600' :
                                memberDetails.fatigue_risk_projection.projected_risk === 'medium' ? 'bg-orange-500' : 'bg-green-600'
                              }>
                                {memberDetails.fatigue_risk_projection.projected_risk?.toUpperCase()}
                              </Badge>
                            </div>
                            <div className="flex justify-between">
                              <span>Fatigue Score:</span>
                              <span className="font-medium">
                                {memberDetails.fatigue_risk_projection.current_fatigue_score}/100
                              </span>
                            </div>
                          </div>
                        </div>
                        
                        <div>
                          <h4 className="font-semibold mb-3">Risk Factors</h4>
                          {memberDetails.fatigue_risk_projection.risk_factors.length > 0 ? (
                            memberDetails.fatigue_risk_projection.risk_factors.map((factor, index) => (
                              <p key={index} className="text-sm text-red-600 mb-1">⚠️ {factor}</p>
                            ))
                          ) : (
                            <p className="text-sm text-green-600">✅ No significant risk factors identified</p>
                          )}
                        </div>
                      </div>
                      
                      {memberDetails.fatigue_risk_projection.recommendations.length > 0 && (
                        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                          <h4 className="font-semibold text-blue-800 mb-2">Recommendations</h4>
                          {memberDetails.fatigue_risk_projection.recommendations.map((rec, index) => (
                            <p key={index} className="text-sm text-blue-700 mb-1">💡 {rec}</p>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              )}

              {activeTab === 'schedule' && memberDetails && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Calendar className="w-5 h-5" />
                      <span>Schedule & Request History</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {memberDetails.schedule_request_history.map((request, index) => (
                        <div key={index} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                          <div>
                            <p className="font-medium text-sm">{request.type}</p>
                            <p className="text-xs text-slate-600">{request.details}</p>
                            <p className="text-xs text-slate-500">{formatDate(request.date)}</p>
                          </div>
                          <Badge className={
                            request.status === 'Approved' ? 'bg-green-600' :
                            request.status === 'Pending' ? 'bg-orange-500' : 'bg-red-600'
                          }>
                            {request.status}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {activeTab === 'equity' && memberDetails && (
                <div className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <Scale className="w-5 h-5 text-green-600" />
                        <span>Equity & Fairness Tracking</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div>
                          <h4 className="font-semibold mb-3">Corro Allocation</h4>
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span>Member Count:</span>
                              <span className="font-medium">{memberDetails.equity_tracking.corro_allocation.member_count}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Station Average:</span>
                              <span className="font-medium">{memberDetails.equity_tracking.corro_allocation.station_average}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Percentile:</span>
                              <span className="font-medium">{memberDetails.equity_tracking.corro_allocation.percentile}th</span>
                            </div>
                          </div>
                        </div>
                        
                        <div>
                          <h4 className="font-semibold mb-3">Shift Distribution</h4>
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span>Van Shifts:</span>
                              <span className="font-medium">{memberDetails.equity_tracking.shift_distribution.van_shifts}%</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Watchhouse:</span>
                              <span className="font-medium">{memberDetails.equity_tracking.shift_distribution.watchhouse_shifts}%</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Night Shifts:</span>
                              <span className="font-medium">{memberDetails.equity_tracking.shift_distribution.night_shifts}%</span>
                            </div>
                          </div>
                        </div>
                        
                        <div>
                          <h4 className="font-semibold mb-3">Overall Fairness</h4>
                          <div className="text-center">
                            <div className="text-3xl font-bold text-green-600 mb-2">
                              {memberDetails.equity_tracking.fairness_score}
                            </div>
                            <p className="text-sm text-slate-600">Fairness Score</p>
                            <div className="mt-2">
                              <Badge className={
                                memberDetails.equity_tracking.fairness_score >= 80 ? 'bg-green-600' :
                                memberDetails.equity_tracking.fairness_score >= 60 ? 'bg-orange-500' : 'bg-red-600'
                              }>
                                {memberDetails.equity_tracking.fairness_score >= 80 ? 'EXCELLENT' :
                                 memberDetails.equity_tracking.fairness_score >= 60 ? 'GOOD' : 'NEEDS ATTENTION'}
                              </Badge>
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Automated Roster Producer Component
const RosterProducer = ({ user }) => {
  const [rosterPeriods, setRosterPeriods] = useState([]);
  const [currentRoster, setCurrentRoster] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [showGenerator, setShowGenerator] = useState(false);
  const [generationConfig, setGenerationConfig] = useState({
    station: user?.station || 'geelong',
    period_weeks: 2,
    min_van_coverage: 2,
    min_watchhouse_coverage: 1,
    max_consecutive_nights: 7,
    min_rest_days_per_fortnight: 4,
    max_fortnight_hours: 76.0,
    enable_fatigue_balancing: true,
    enable_preference_weighting: true,
    corro_rotation_priority: true
  });

  useEffect(() => {
    fetchRosterPeriods();
  }, []);

  const fetchRosterPeriods = async () => {
    try {
      const response = await axios.get(`${API}/roster/periods?station=${user?.station}`);
      setRosterPeriods(response.data);
    } catch (error) {
      console.error('Failed to fetch roster periods:', error);
    }
  };

  const generateNewRoster = async () => {
    setGenerating(true);
    try {
      const response = await axios.post(`${API}/roster/generate`, generationConfig);
      console.log('Roster generated:', response.data);
      
      // Refresh roster periods
      await fetchRosterPeriods();
      
      // Load the newly generated roster
      const rosterDetails = await axios.get(`${API}/roster/${response.data.roster_period_id}`);
      setCurrentRoster(rosterDetails.data);
      
      setShowGenerator(false);
    } catch (error) {
      console.error('Failed to generate roster:', error);
    } finally {
      setGenerating(false);
    }
  };

  const loadRosterDetails = async (rosterId) => {
    try {
      const response = await axios.get(`${API}/roster/${rosterId}`);
      setCurrentRoster(response.data);
    } catch (error) {
      console.error('Failed to load roster details:', error);
    }
  };

  const publishRoster = async (rosterId) => {
    try {
      await axios.put(`${API}/roster/${rosterId}/publish`);
      await fetchRosterPeriods();
      // Refresh current roster if it's the one being published
      if (currentRoster?.roster_period.id === rosterId) {
        await loadRosterDetails(rosterId);
      }
    } catch (error) {
      console.error('Failed to publish roster:', error);
      alert('Failed to publish roster. Please check for EBA compliance violations.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center space-x-2">
                <Calendar className="w-5 h-5 text-blue-600" />
                <span>Automated Roster Producer</span>
                <Badge className="bg-blue-100 text-blue-800">Phase 1</Badge>
              </CardTitle>
              <p className="text-slate-600 mt-1">
                Generate EBA-compliant, fair, and fatigue-conscious rosters automatically
              </p>
            </div>
            {(user?.role === 'sergeant' || user?.role === 'inspector' || user?.role === 'admin') && (
              <Button 
                onClick={() => setShowGenerator(true)}
                className="bg-blue-600 hover:bg-blue-700"
                disabled={generating}
              >
                <Zap className="w-4 h-4 mr-2" />
                Generate New Roster
              </Button>
            )}
          </div>
        </CardHeader>
      </Card>

      {/* Roster Generation Modal */}
      {showGenerator && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-6">
              <h3 className="text-xl font-bold">Generate New Roster</h3>
              <p className="text-blue-100">Configure automatic roster generation settings</p>
            </div>
            
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label className="text-base font-semibold">Station</Label>
                  <Select 
                    value={generationConfig.station} 
                    onValueChange={(value) => setGenerationConfig({...generationConfig, station: value})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="geelong">Geelong</SelectItem>
                      <SelectItem value="corio">Corio</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label className="text-base font-semibold">Period Length</Label>
                  <Select 
                    value={generationConfig.period_weeks.toString()} 
                    onValueChange={(value) => setGenerationConfig({...generationConfig, period_weeks: parseInt(value)})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1 Week</SelectItem>
                      <SelectItem value="2">2 Weeks (Fortnight)</SelectItem>
                      <SelectItem value="4">4 Weeks</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label className="text-base font-semibold">Min Van Coverage</Label>
                  <Input 
                    type="number" 
                    value={generationConfig.min_van_coverage}
                    onChange={(e) => setGenerationConfig({...generationConfig, min_van_coverage: parseInt(e.target.value)})}
                    min="1" max="5"
                  />
                </div>
                
                <div>
                  <Label className="text-base font-semibold">Min Watchhouse Coverage</Label>
                  <Input 
                    type="number" 
                    value={generationConfig.min_watchhouse_coverage}
                    onChange={(e) => setGenerationConfig({...generationConfig, min_watchhouse_coverage: parseInt(e.target.value)})}
                    min="1" max="3"
                  />
                </div>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <Switch 
                    checked={generationConfig.enable_fatigue_balancing}
                    onCheckedChange={(checked) => setGenerationConfig({...generationConfig, enable_fatigue_balancing: checked})}
                  />
                  <div>
                    <Label className="text-base font-medium">Enable Fatigue Balancing</Label>
                    <p className="text-sm text-slate-500">Distribute high-fatigue shifts fairly</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3">
                  <Switch 
                    checked={generationConfig.enable_preference_weighting}
                    onCheckedChange={(checked) => setGenerationConfig({...generationConfig, enable_preference_weighting: checked})}
                  />
                  <div>
                    <Label className="text-base font-medium">Consider Member Preferences</Label>
                    <p className="text-sm text-slate-500">Weight assignments based on member preferences</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3">
                  <Switch 
                    checked={generationConfig.corro_rotation_priority}
                    onCheckedChange={(checked) => setGenerationConfig({...generationConfig, corro_rotation_priority: checked})}
                  />
                  <div>
                    <Label className="text-base font-medium">Fair Corro Rotation</Label>
                    <p className="text-sm text-slate-500">Ensure fair distribution of corro days</p>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="bg-slate-50 px-6 py-4 flex justify-end space-x-3 border-t">
              <Button 
                variant="outline" 
                onClick={() => setShowGenerator(false)}
              >
                Cancel
              </Button>
              <Button 
                onClick={generateNewRoster} 
                disabled={generating}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {generating ? (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Generating...</span>
                  </div>
                ) : (
                  <>
                    <Zap className="w-4 h-4 mr-2" />
                    Generate Roster
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Roster Periods List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Roster Periods</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {rosterPeriods.slice(0, 10).map((period) => (
                <div 
                  key={period.id} 
                  className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 cursor-pointer transition-colors"
                  onClick={() => loadRosterDetails(period.id)}
                >
                  <div>
                    <p className="font-medium">
                      {formatDate(period.start_date)} - {formatDate(period.end_date)}
                    </p>
                    <p className="text-sm text-slate-600 capitalize">
                      {period.station} • {period.status}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge className={
                      period.status === 'published' ? 'bg-green-600' :
                      period.status === 'draft' ? 'bg-orange-500' : 'bg-gray-500'
                    }>
                      {period.status.toUpperCase()}
                    </Badge>
                    {period.status === 'draft' && (user?.role === 'sergeant' || user?.role === 'inspector' || user?.role === 'admin') && (
                      <Button 
                        size="sm" 
                        onClick={(e) => {
                          e.stopPropagation();
                          publishRoster(period.id);
                        }}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        Publish
                      </Button>
                    )}
                  </div>
                </div>
              ))}
              
              {rosterPeriods.length === 0 && (
                <div className="text-center py-8 text-slate-500">
                  <Calendar className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No roster periods found</p>
                  <p className="text-sm">Generate your first automated roster to get started</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Current Roster Details */}
        <Card>
          <CardHeader>
            <CardTitle>
              {currentRoster ? 'Roster Details' : 'Select a Roster'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {currentRoster ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-slate-600">Period:</span>
                    <p className="font-medium">
                      {formatDate(currentRoster.roster_period.start_date)} - {formatDate(currentRoster.roster_period.end_date)}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-600">Status:</span>
                    <Badge className={
                      currentRoster.roster_period.status === 'published' ? 'bg-green-600' :
                      currentRoster.roster_period.status === 'draft' ? 'bg-orange-500' : 'bg-gray-500'
                    }>
                      {currentRoster.roster_period.status.toUpperCase()}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-slate-600">Total Assignments:</span>
                    <p className="font-medium">{currentRoster.total_assignments}</p>
                  </div>
                  <div>
                    <span className="text-slate-600">Station:</span>
                    <p className="font-medium capitalize">{currentRoster.roster_period.station}</p>
                  </div>
                </div>
                
                {/* Compliance Status */}
                <div className="mt-4 p-3 rounded-lg" style={{
                  backgroundColor: currentRoster.compliance_status.has_violations ? '#fef2f2' : '#f0fdf4',
                  border: `1px solid ${currentRoster.compliance_status.has_violations ? '#fecaca' : '#bbf7d0'}`
                }}>
                  <h4 className={`font-semibold text-sm mb-2 ${
                    currentRoster.compliance_status.has_violations ? 'text-red-800' : 'text-green-800'
                  }`}>
                    EBA Compliance Status
                  </h4>
                  
                  {currentRoster.compliance_status.has_violations ? (
                    <div>
                      <p className="text-red-700 text-sm mb-2">⚠️ {currentRoster.compliance_status.violations.length} violations found</p>
                      {currentRoster.compliance_status.violations.slice(0, 3).map((violation, index) => (
                        <p key={index} className="text-xs text-red-600 mb-1">• {violation}</p>
                      ))}
                    </div>
                  ) : (
                    <p className="text-green-700 text-sm">✅ All EBA compliance rules satisfied</p>
                  )}
                </div>
                
                {/* Member Summary */}
                <div className="mt-4">
                  <h4 className="font-semibold text-sm mb-2">Member Assignment Summary</h4>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {Object.entries(currentRoster.member_summary).slice(0, 6).map(([memberId, summary]) => (
                      <div key={memberId} className="flex justify-between text-sm">
                        <span>{summary.name}</span>
                        <span className="text-slate-600">{summary.total_shifts} shifts • {summary.total_hours}h</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500">
                <Eye className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Select a roster period to view details</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" />;
};

// Main App Component
function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;