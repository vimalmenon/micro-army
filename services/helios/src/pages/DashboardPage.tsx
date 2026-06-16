import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActionArea from '@mui/material/CardActionArea';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import OpenInNewRoundedIcon from '@mui/icons-material/OpenInNewRounded';
import ShieldRoundedIcon from '@mui/icons-material/ShieldRounded';
import EmailRoundedIcon from '@mui/icons-material/EmailRounded';
import MenuBookRoundedIcon from '@mui/icons-material/MenuBookRounded';
import ApiRoundedIcon from '@mui/icons-material/ApiRounded';
import PlayCircleRoundedIcon from '@mui/icons-material/PlayCircleRounded';
import MonitorHeartRoundedIcon from '@mui/icons-material/MonitorHeartRounded';
import LockRoundedIcon from '@mui/icons-material/LockRounded';
import DnsRoundedIcon from '@mui/icons-material/DnsRounded';
import AccountTreeRoundedIcon from '@mui/icons-material/AccountTreeRounded';
import WebRoundedIcon from '@mui/icons-material/WebRounded';
import SettingsRoundedIcon from '@mui/icons-material/SettingsRounded';
import SlideshowRoundedIcon from '@mui/icons-material/SlideshowRounded';
import AdsClickRoundedIcon from '@mui/icons-material/AdsClickRounded';
import RouterRoundedIcon from '@mui/icons-material/RouterRounded';
import CloudQueueRoundedIcon from '@mui/icons-material/CloudQueueRounded';
import StorageRoundedIcon from '@mui/icons-material/StorageRounded';
import DashboardRoundedIcon from '@mui/icons-material/DashboardRounded';

interface AppLink {
  name: string;
  url: string;
  description: string;
  icon: React.ReactNode;
  category: string;
  tags?: string[];
  internal?: boolean;
}

const apps: AppLink[] = [
  {
    name: 'Admin Dashboard',
    url: 'https://admin.completeautomate.com',
    description: 'Helios admin panel — messages, leads, services',
    icon: <DashboardRoundedIcon fontSize="large" />,
    category: 'Core',
    tags: ['MUI'],
  },
  {
    name: 'Messages API',
    url: 'https://messages.completeautomate.com',
    description: 'Angelos — customer email / message processing endpoint',
    icon: <EmailRoundedIcon fontSize="large" />,
    category: 'Core',
    tags: ['API'],
  },
  {
    name: 'ArgoCD',
    url: 'https://argocd.completeautomate.com',
    description: 'GitOps deployment — sync & manage all k8s apps',
    icon: <CloudQueueRoundedIcon fontSize="large" />,
    category: 'Infra',
    tags: ['GitOps'],
  },
  {
    name: 'Hestia API',
    url: 'https://hestia.completeautomate.com/docs',
    description: 'Backend API (FastAPI) — service health & data endpoints',
    icon: <ApiRoundedIcon fontSize="large" />,
    category: 'Core',
    tags: ['Swagger', 'FastAPI'],
  },
  {
    name: 'Wiki',
    url: 'https://wiki.completeautomate.com',
    description: 'Athena — documentation & knowledge base',
    icon: <MenuBookRoundedIcon fontSize="large" />,
    category: 'Core',
    tags: ['Docs'],
  },
  {
    name: 'Ops (Semaphore)',
    url: 'https://ops.completeautomate.com',
    description: 'Ansible automation — run playbooks & manage infra',
    icon: <PlayCircleRoundedIcon fontSize="large" />,
    category: 'Infra',
    tags: ['Ansible'],
  },
  {
    name: 'Status',
    url: 'https://status.completeautomate.com',
    description: 'Uptime Kuma — real-time service health monitoring',
    icon: <MonitorHeartRoundedIcon fontSize="large" />,
    category: 'Infra',
    tags: ['Monitoring'],
  },
  {
    name: 'Vault',
    url: 'https://vault.completeautomate.com',
    description: 'Vaultwarden — password & credential management',
    icon: <LockRoundedIcon fontSize="large" />,
    category: 'Infra',
    tags: ['Security'],
  },
  {
    name: 'n8n',
    url: 'https://n8n.completeautomate.com',
    description: 'Workflow automation — connect APIs & automate tasks',
    icon: <AccountTreeRoundedIcon fontSize="large" />,
    category: 'Automation',
    tags: ['Workflows'],
  },
  {
    name: 'Homepage',
    url: 'https://homepage.completeautomate.com',
    description: 'Custom start page with bookmarks & widgets',
    icon: <WebRoundedIcon fontSize="large" />,
    category: 'Other',
    tags: ['Startpage'],
  },
  {
    name: 'NetAlertX',
    url: 'https://netalertx.completeautomate.com',
    description: 'Network monitoring — device discovery & alerts',
    icon: <RouterRoundedIcon fontSize="large" />,
    category: 'Infra',
    tags: ['Network'],
  },
  {
    name: 'Slides',
    url: 'https://slides.completeautomate.com',
    description: 'Presentation slides & content displays',
    icon: <SlideshowRoundedIcon fontSize="large" />,
    category: 'Other',
    tags: ['Presentations'],
  },
  {
    name: 'Auth (Authelia)',
    url: 'https://auth.completeautomate.com',
    description: 'SSO & authentication gateway for all services',
    icon: <ShieldRoundedIcon fontSize="large" />,
    category: 'Infra',
    tags: ['SSO'],
  },
  {
    name: 'ArgoCD CLI',
    url: 'https://argocd.completeautomate.com/settings',
    description: 'ArgoCD settings & project configuration',
    icon: <SettingsRoundedIcon fontSize="large" />,
    category: 'Infra',
    tags: ['Admin'],
  },
  {
    name: 'Pi-hole',
    url: 'http://pihole.homelab.local/admin',
    description: 'DNS ad-blocking & network-wide blocker (LAN only)',
    icon: <DnsRoundedIcon fontSize="large" />,
    category: 'Infra',
    tags: ['DNS', 'LAN'],
    internal: true,
  },
  {
    name: 'YouTube',
    url: 'http://youtube.homelab.local',
    description: 'Orpheus — YouTube content processing (LAN only)',
    icon: <AdsClickRoundedIcon fontSize="large" />,
    category: 'Other',
    tags: ['Media', 'LAN'],
    internal: true,
  },
];

const categoryColors: Record<string, string> = {
  Core: 'primary.main',
  Infra: 'warning.main',
  Automation: 'success.main',
  Other: 'text.secondary',
};

export function DashboardPage() {
  const categories = [...new Set(apps.map((a) => a.category))];

  return (
    <Box sx={{ p: 1 }}>
      <Typography variant="h4" sx={{ mb: 1, fontWeight: 700 }}>
        Bookmarks
      </Typography>
      <Typography variant="body2" sx={{ mb: 4, color: 'text.secondary' }}>
        Quick access to all services — click to open in a new tab
      </Typography>

      {categories.map((category) => (
        <Box key={category} sx={{ mb: 4 }}>
          <Typography
            variant="subtitle1"
            sx={{
              mb: 2,
              fontWeight: 600,
              color: categoryColors[category] || 'text.secondary',
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            }}
          >
            {category}
          </Typography>
          <Grid container spacing={2}>
            {apps
              .filter((a) => a.category === category)
              .map((app) => (
                <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={app.name}>
                  <Card
                    variant="outlined"
                    sx={{
                      height: '100%',
                      transition: 'all 0.2s ease',
                      '&:hover': {
                        borderColor: 'primary.main',
                        boxShadow: 2,
                        transform: 'translateY(-2px)',
                      },
                    }}
                  >
                    <CardActionArea
                      href={app.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      sx={{ height: '100%', p: 1.5 }}
                    >
                      <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
                        <Box
                          sx={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1.5,
                            mb: 1,
                          }}
                        >
                          <Box sx={{ color: 'primary.main', lineHeight: 0 }}>
                            {app.icon}
                          </Box>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                            {app.name}
                          </Typography>
                        </Box>
                        <Typography
                          variant="body2"
                          sx={{ color: 'text.secondary', mb: 1.5, lineHeight: 1.4 }}
                        >
                          {app.description}
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          <Chip
                            label={app.internal ? 'LAN' : 'Public'}
                            size="small"
                            color={app.internal ? 'default' : 'success'}
                            variant="outlined"
                            sx={{ height: 20, fontSize: '0.7rem' }}
                          />
                          {app.tags?.map((tag) => (
                            <Chip
                              key={tag}
                              label={tag}
                              size="small"
                              variant="outlined"
                              sx={{ height: 20, fontSize: '0.7rem' }}
                            />
                          ))}
                        </Box>
                      </CardContent>
                    </CardActionArea>
                  </Card>
                </Grid>
              ))}
          </Grid>
        </Box>
      ))}
    </Box>
  );
}
