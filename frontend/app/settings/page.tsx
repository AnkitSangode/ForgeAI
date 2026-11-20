
"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import {
  Settings2,
  User,
  Building2,
  Bot,
  Bell,
  Shield,
  KeyRound,
  Save,
  Check,
  ChevronRight,
  Globe,
  Cpu,
  Zap,
  Clock3,
  Mail,
  MessageSquare,
  AlertTriangle,
  Lock,
  Eye,
  EyeOff,
  RefreshCw,
  Code2,
} from "lucide-react";

import DashboardLayout from "@/components/layout/dashboard-layout";

type SettingsTab =
  | "profile"
  | "workspace"
  | "agents"
  | "notifications"
  | "security";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");
  const [saved, setSaved] = useState(false);

  const [profile, setProfile] = useState({
    name: "Workspace Owner",
    email: "owner@forgeai.dev",
    role: "Administrator",
    timezone: "Asia/Kolkata",
  });

  const [workspace, setWorkspace] = useState({
    name: "ForgeAI Workspace",
    description: "Autonomous software engineering workspace",
    defaultBranch: "main",
    repositoryAccess: "Private repositories",
  });

  const [agentSettings, setAgentSettings] = useState({
    autoReview: true,
    requireApproval: true,
    runTests: true,
    autoFix: false,
    maxRetries: "3",
    executionTimeout: "30",
    model: "GPT-4o",
  });

  const [notifications, setNotifications] = useState({
    taskCompleted: true,
    taskFailed: true,
    reviewRequired: true,
    agentActivity: false,
    emailNotifications: true,
    inAppNotifications: true,
  });

  const [security, setSecurity] = useState({
    twoFactor: false,
    sessionTimeout: "60",
    auditLogs: true,
  });

  const [showApiKey, setShowApiKey] = useState(false);

  function handleSave() {
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2500);
  }

  function updateAgentSetting(
    key: keyof typeof agentSettings,
    value: string | boolean
  ) {
    setAgentSettings((current) => ({ ...current, [key]: value }));
  }

  function updateNotification(
    key: keyof typeof notifications,
    value: boolean
  ) {
    setNotifications((current) => ({ ...current, [key]: value }));
  }

  const tabs: { id: SettingsTab; label: string; icon: ReactNode }[] = [
    { id: "profile", label: "Profile", icon: <User size={17} /> },
    { id: "workspace", label: "Workspace", icon: <Building2 size={17} /> },
    { id: "agents", label: "Agent Configuration", icon: <Bot size={17} /> },
    { id: "notifications", label: "Notifications", icon: <Bell size={17} /> },
    { id: "security", label: "Security", icon: <Shield size={17} /> },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-6 pb-10">
        {/* Heading */}
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm text-zinc-500">
            <span>Workspace</span>
            <ChevronRight size={14} />
            <span className="text-zinc-300">Settings</span>
          </div>

          <h1 className="text-2xl font-semibold text-white">Settings</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Manage your workspace, autonomous agents, and platform preferences.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[250px_minmax(0,1fr)]">
          {/* Settings navigation */}
          <aside className="dashboard-card h-fit rounded-xl border border-[#27272f] bg-[#111114] p-3">
            <div className="mb-3 px-3 py-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                General
              </p>
            </div>

            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition ${
                    activeTab === tab.id
                      ? "bg-violet-500/15 text-violet-300"
                      : "text-zinc-400 hover:bg-white/[0.04] hover:text-white"
                  }`}
                >
                  {tab.icon}
                  <span>{tab.label}</span>
                  {activeTab === tab.id && (
                    <ChevronRight size={15} className="ml-auto" />
                  )}
                </button>
              ))}
            </nav>

            <div className="mt-5 border-t border-[#27272f] pt-4">
              <div className="rounded-lg border border-violet-500/20 bg-violet-500/[0.06] p-3">
                <div className="flex items-center gap-2 text-violet-300">
                  <Zap size={15} />
                  <span className="text-xs font-semibold">ForgeAI</span>
                </div>
                <p className="mt-2 text-xs leading-5 text-zinc-500">
                  Autonomous engineering workspace
                </p>
                <p className="mt-2 text-[10px] text-zinc-600">
                  Frontend preview · v0.1.0
                </p>
              </div>
            </div>
          </aside>

          {/* Settings content */}
          <main className="min-w-0 space-y-5">
            {activeTab === "profile" && (
              <>
                <SectionHeader
                  title="Profile Settings"
                  description="Manage your personal account information."
                  icon={<User size={18} />}
                />

                <SettingsCard title="Personal Information">
                  <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
                    <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-violet-500/30 bg-violet-500/15 text-xl font-semibold text-violet-300">
                      WO
                    </div>
                    <div>
                      <p className="font-medium text-white">{profile.name}</p>
                      <p className="mt-1 text-sm text-zinc-500">
                        {profile.email}
                      </p>
                      <span className="mt-2 inline-flex rounded-md border border-violet-500/20 bg-violet-500/10 px-2 py-1 text-[10px] text-violet-300">
                        {profile.role}
                      </span>
                    </div>
                  </div>

                  <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <FormField label="Full name">
                      <input
                        value={profile.name}
                        onChange={(e) =>
                          setProfile({ ...profile, name: e.target.value })
                        }
                        className="settings-input"
                      />
                    </FormField>

                    <FormField label="Email address">
                      <input
                        type="email"
                        value={profile.email}
                        onChange={(e) =>
                          setProfile({ ...profile, email: e.target.value })
                        }
                        className="settings-input"
                      />
                    </FormField>

                    <FormField label="Account role">
                      <input
                        value={profile.role}
                        disabled
                        className="settings-input opacity-60"
                      />
                    </FormField>

                    <FormField label="Timezone">
                      <select
                        value={profile.timezone}
                        onChange={(e) =>
                          setProfile({ ...profile, timezone: e.target.value })
                        }
                        className="settings-input"
                      >
                        <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                        <option value="UTC">UTC</option>
                        <option value="America/New_York">
                          America/New_York
                        </option>
                        <option value="Europe/London">Europe/London</option>
                      </select>
                    </FormField>
                  </div>
                </SettingsCard>
              </>
            )}

            {activeTab === "workspace" && (
              <>
                <SectionHeader
                  title="Workspace Settings"
                  description="Configure your engineering workspace."
                  icon={<Building2 size={18} />}
                />

                <SettingsCard title="Workspace Information">
                  <div className="space-y-4">
                    <FormField label="Workspace name">
                      <input
                        value={workspace.name}
                        onChange={(e) =>
                          setWorkspace({ ...workspace, name: e.target.value })
                        }
                        className="settings-input"
                      />
                    </FormField>

                    <FormField label="Description">
                      <textarea
                        rows={3}
                        value={workspace.description}
                        onChange={(e) =>
                          setWorkspace({
                            ...workspace,
                            description: e.target.value,
                          })
                        }
                        className="settings-input resize-y"
                      />
                    </FormField>

                    <FormField label="Default Git branch">
                      <input
                        value={workspace.defaultBranch}
                        onChange={(e) =>
                          setWorkspace({
                            ...workspace,
                            defaultBranch: e.target.value,
                          })
                        }
                        className="settings-input"
                      />
                    </FormField>

                    <FormField label="Repository access">
                      <select
                        value={workspace.repositoryAccess}
                        onChange={(e) =>
                          setWorkspace({
                            ...workspace,
                            repositoryAccess: e.target.value,
                          })
                        }
                        className="settings-input"
                      >
                        <option>Private repositories</option>
                        <option>Public repositories</option>
                        <option>All repositories</option>
                      </select>
                    </FormField>
                  </div>
                </SettingsCard>

                <SettingsCard title="Repository Integration">
                  <IntegrationRow
                    icon={<Code2 size={20} />}
                    name="GitHub"
                    description="Connect repositories for autonomous development."
                    status="Not connected"
                  />
                  <div className="mt-4 border-t border-[#27272f] pt-4">
                    <IntegrationRow
                      icon={<Globe size={20} />}
                      name="Git Provider"
                      description="Repository provider integration will be configured here."
                      status="Coming soon"
                    />
                  </div>
                </SettingsCard>
              </>
            )}

            {activeTab === "agents" && (
              <>
                <SectionHeader
                  title="Agent Configuration"
                  description="Define how autonomous agents behave during execution."
                  icon={<Bot size={18} />}
                />

                <SettingsCard title="AI Model Configuration">
                  <FormField label="Default language model">
                    <select
                      value={agentSettings.model}
                      onChange={(e) =>
                        updateAgentSetting("model", e.target.value)
                      }
                      className="settings-input"
                    >
                      <option>GPT-4o</option>
                      <option>GPT-4o-mini</option>
                      <option>Gemini</option>
                      <option>Claude</option>
                      <option>Local model</option>
                    </select>
                  </FormField>

                  <div className="mt-4 flex items-start gap-3 rounded-lg border border-violet-500/20 bg-violet-500/[0.06] p-3">
                    <Cpu size={18} className="mt-0.5 text-violet-300" />
                    <div>
                      <p className="text-sm font-medium text-violet-200">
                        Model provider configuration
                      </p>
                      <p className="mt-1 text-xs leading-5 text-zinc-500">
                        This selection is a frontend preference only. Actual
                        provider routing will be handled by the backend.
                      </p>
                    </div>
                  </div>
                </SettingsCard>

                <SettingsCard title="Execution Policies">
                  <div className="space-y-4">
                    <ToggleRow
                      label="Automatic code review"
                      description="Run a review after code generation."
                      checked={agentSettings.autoReview}
                      onChange={(value) =>
                        updateAgentSetting("autoReview", value)
                      }
                    />
                    <ToggleRow
                      label="Require human approval"
                      description="Require human approval before sensitive actions."
                      checked={agentSettings.requireApproval}
                      onChange={(value) =>
                        updateAgentSetting("requireApproval", value)
                      }
                    />
                    <ToggleRow
                      label="Run tests automatically"
                      description="Execute available tests after code changes."
                      checked={agentSettings.runTests}
                      onChange={(value) =>
                        updateAgentSetting("runTests", value)
                      }
                    />
                    <ToggleRow
                      label="Allow automatic fixes"
                      description="Allow agents to attempt fixes when tests fail."
                      checked={agentSettings.autoFix}
                      onChange={(value) =>
                        updateAgentSetting("autoFix", value)
                      }
                    />
                  </div>
                </SettingsCard>

                <SettingsCard title="Execution Limits">
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <FormField label="Maximum retry attempts">
                      <select
                        value={agentSettings.maxRetries}
                        onChange={(e) =>
                          updateAgentSetting("maxRetries", e.target.value)
                        }
                        className="settings-input"
                      >
                        <option value="1">1 attempt</option>
                        <option value="2">2 attempts</option>
                        <option value="3">3 attempts</option>
                        <option value="5">5 attempts</option>
                      </select>
                    </FormField>

                    <FormField label="Execution timeout">
                      <select
                        value={agentSettings.executionTimeout}
                        onChange={(e) =>
                          updateAgentSetting(
                            "executionTimeout",
                            e.target.value
                          )
                        }
                        className="settings-input"
                      >
                        <option value="10">10 minutes</option>
                        <option value="30">30 minutes</option>
                        <option value="60">60 minutes</option>
                        <option value="120">120 minutes</option>
                      </select>
                    </FormField>
                  </div>
                </SettingsCard>
              </>
            )}

            {activeTab === "notifications" && (
              <>
                <SectionHeader
                  title="Notification Preferences"
                  description="Choose which platform events you want to receive."
                  icon={<Bell size={18} />}
                />

                <SettingsCard title="Delivery Channels">
                  <div className="space-y-4">
                    <ToggleRow
                      icon={<Mail size={17} />}
                      label="Email notifications"
                      description="Receive important updates through email."
                      checked={notifications.emailNotifications}
                      onChange={(value) =>
                        updateNotification("emailNotifications", value)
                      }
                    />
                    <ToggleRow
                      icon={<MessageSquare size={17} />}
                      label="In-app notifications"
                      description="Show notifications inside your ForgeAI workspace."
                      checked={notifications.inAppNotifications}
                      onChange={(value) =>
                        updateNotification("inAppNotifications", value)
                      }
                    />
                  </div>
                </SettingsCard>

                <SettingsCard title="Event Notifications">
                  <div className="space-y-4">
                    <ToggleRow
                      label="Task completed"
                      description="Notify me when an engineering task finishes."
                      checked={notifications.taskCompleted}
                      onChange={(value) =>
                        updateNotification("taskCompleted", value)
                      }
                    />
                    <ToggleRow
                      label="Task failed"
                      description="Notify me when a task fails."
                      checked={notifications.taskFailed}
                      onChange={(value) =>
                        updateNotification("taskFailed", value)
                      }
                    />
                    <ToggleRow
                      label="Human review required"
                      description="Notify me when an agent needs approval."
                      checked={notifications.reviewRequired}
                      onChange={(value) =>
                        updateNotification("reviewRequired", value)
                      }
                    />
                    <ToggleRow
                      label="Agent activity"
                      description="Receive updates about agent execution activity."
                      checked={notifications.agentActivity}
                      onChange={(value) =>
                        updateNotification("agentActivity", value)
                      }
                    />
                  </div>
                </SettingsCard>
              </>
            )}

            {activeTab === "security" && (
              <>
                <SectionHeader
                  title="Security Settings"
                  description="Manage account protection and workspace security."
                  icon={<Shield size={18} />}
                />

                <SettingsCard title="Authentication">
                  <ToggleRow
                    icon={<Lock size={17} />}
                    label="Two-factor authentication"
                    description="Add an additional authentication step to your account."
                    checked={security.twoFactor}
                    onChange={(value) =>
                      setSecurity({ ...security, twoFactor: value })
                    }
                  />

                  <div className="mt-5 border-t border-[#27272f] pt-5">
                    <FormField label="Session timeout">
                      <select
                        value={security.sessionTimeout}
                        onChange={(e) =>
                          setSecurity({
                            ...security,
                            sessionTimeout: e.target.value,
                          })
                        }
                        className="settings-input"
                      >
                        <option value="15">15 minutes</option>
                        <option value="30">30 minutes</option>
                        <option value="60">60 minutes</option>
                        <option value="120">2 hours</option>
                      </select>
                    </FormField>
                  </div>
                </SettingsCard>

                <SettingsCard title="API Key Management">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-zinc-800 p-2 text-zinc-300">
                      <KeyRound size={19} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-white">
                        Workspace API Key
                      </p>
                      <p className="mt-1 text-xs text-zinc-500">
                        Example display only. No real API key is configured here.
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center gap-2 rounded-lg border border-[#303039] bg-[#09090b] px-3 py-2.5">
                    <code className="min-w-0 flex-1 truncate text-xs text-zinc-400">
                      {showApiKey
                        ? "forgeai_demo_key_not_a_real_secret"
                        : "••••••••••••••••••••••••"}
                    </code>
                    <button
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="text-zinc-500 hover:text-white"
                      aria-label={showApiKey ? "Hide API key" : "Show API key"}
                    >
                      {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </SettingsCard>

                <SettingsCard title="Audit & Activity">
                  <ToggleRow
                    label="Enable audit logs"
                    description="Keep a record of important workspace actions."
                    checked={security.auditLogs}
                    onChange={(value) =>
                      setSecurity({ ...security, auditLogs: value })
                    }
                  />
                </SettingsCard>

                <div className="rounded-xl border border-red-500/20 bg-red-500/[0.04] p-5">
                  <div className="flex items-center gap-2 text-red-300">
                    <AlertTriangle size={18} />
                    <h3 className="text-sm font-semibold">Danger Zone</h3>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-zinc-500">
                    Account deletion and workspace data removal are not
                    implemented in this frontend preview.
                  </p>
                  <button
                    disabled
                    className="mt-4 cursor-not-allowed rounded-lg border border-red-500/20 px-3 py-2 text-xs text-red-400 opacity-50"
                  >
                    Delete workspace
                  </button>
                </div>
              </>
            )}

            {/* Save action */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#27272f] pt-5">
              <p className="text-xs text-zinc-600">
                Changes are currently stored in page state only.
              </p>

              <button
                onClick={handleSave}
                className="flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-violet-500"
              >
                {saved ? <Check size={16} /> : <Save size={16} />}
                {saved ? "Saved locally" : "Save Changes"}
              </button>
            </div>
          </main>
        </div>
      </div>
    </DashboardLayout>
  );
}

function SectionHeader({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon: ReactNode;
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="rounded-lg border border-violet-500/20 bg-violet-500/10 p-2.5 text-violet-300">
        {icon}
      </div>
      <div>
        <h2 className="font-semibold text-white">{title}</h2>
        <p className="mt-1 text-xs text-zinc-500">{description}</p>
      </div>
    </div>
  );
}

function SettingsCard({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="dashboard-card rounded-xl border border-[#27272f] bg-[#111114] p-5">
      <h3 className="mb-5 text-sm font-semibold text-white">{title}</h3>
      {children}
    </section>
  );
}

function FormField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="block space-y-2">
      <span className="text-xs font-medium text-zinc-400">{label}</span>
      {children}
    </label>
  );
}

function ToggleRow({
  icon,
  label,
  description,
  checked,
  onChange,
}: {
  icon?: ReactNode;
  label: string;
  description: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="flex min-w-0 items-start gap-3">
        {icon && (
          <span className="mt-0.5 text-zinc-500">{icon}</span>
        )}
        <div>
          <p className="text-sm font-medium text-zinc-200">{label}</p>
          <p className="mt-1 text-xs leading-5 text-zinc-500">
            {description}
          </p>
        </div>
      </div>

      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative h-6 w-11 shrink-0 rounded-full transition ${
          checked ? "bg-violet-600" : "bg-zinc-700"
        }`}
      >
        <span
          className={`absolute top-1 h-4 w-4 rounded-full bg-white transition ${
            checked ? "left-6" : "left-1"
          }`}
        />
      </button>
    </div>
  );
}


function IntegrationRow({
  icon,
  name,
  description,
  status,
}: {
  icon: ReactNode;
  name: string;
  description: string;
  status: string;
}) {
  return (
    <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
      <div className="flex min-w-0 items-center gap-3">
        <div className="rounded-lg border border-[#303039] bg-[#09090b] p-2.5 text-zinc-300">
          {icon}
        </div>

        <div className="min-w-0">
          <p className="text-sm font-medium text-white">{name}</p>
          <p className="mt-1 text-xs text-zinc-500">{description}</p>
        </div>
      </div>

      <span className="w-fit shrink-0 rounded-md border border-zinc-700 bg-zinc-800/60 px-2.5 py-1 text-xs text-zinc-400">
        {status}
      </span>
    </div>
  );
}
