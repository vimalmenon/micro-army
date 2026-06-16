import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';

// Icons per service
import EmailRoundedIcon from '@mui/icons-material/EmailRounded';
import DnsRoundedIcon from '@mui/icons-material/DnsRounded';
import MenuBookRoundedIcon from '@mui/icons-material/MenuBookRounded';
import CloudQueueRoundedIcon from '@mui/icons-material/CloudQueueRounded';
import StorageRoundedIcon from '@mui/icons-material/StorageRounded';
import DashboardRoundedIcon from '@mui/icons-material/DashboardRounded';
import ApiRoundedIcon from '@mui/icons-material/ApiRounded';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import SlideshowRoundedIcon from '@mui/icons-material/SlideshowRounded';
import PsychologyRoundedIcon from '@mui/icons-material/PsychologyRounded';
import WebRoundedIcon from '@mui/icons-material/WebRounded';

interface ServiceInfo {
  name: string;
  god: string;
  myth: string;
  function: string;
  description: string;
  icon: React.ReactNode;
  tech: string[];
}

const services: ServiceInfo[] = [
  {
    name: 'Angelos',
    god: 'Ἄγγελος — Messenger Deity',
    myth: 'Divine messenger who delivered news between gods and mortals.',
    function: 'Contact Form API',
    description: 'Processes incoming messages from the Complete Automate website contact form. Validates, stores, and routes inquiries to the right team.',
    icon: <EmailRoundedIcon sx={{ fontSize: 36 }} />,
    tech: ['Python', 'FastAPI', 'DynamoDB'],
  },
  {
    name: 'Arachne',
    god: 'Ἀράχνη — Weaver turned Spider',
    myth: 'Master weaver transformed into a spider, forever weaving webs.',
    function: 'Cloudflare Tunnel Sync',
    description: 'Syncs Cloudflare tunnel configuration, weaving a web of secure connections that expose internal services to the internet.',
    icon: <DnsRoundedIcon sx={{ fontSize: 36 }} />,
    tech: ['Python', 'Cloudflare', 'k8s'],
  },
  {
    name: 'Arch',
    god: 'Ἀρχή — The Beginning / Origin',
    myth: 'The primordial origin — the first principle from which all things flow.',
    function: 'Static File Server',
    description: 'Serves static content for public-facing landing pages and assets. The entry point to the Complete Automate web presence.',
    icon: <WebRoundedIcon sx={{ fontSize: 36 }} />,
    tech: ['Nginx', 'Static'],
  },
  {
    name: 'Athena',
    god: 'Ἀθηνᾶ — Goddess of Wisdom',
    myth: 'Born from Zeus\'s head, goddess of wisdom, crafts, and strategic warfare.',
    function: 'Wiki / Knowledge Base',
    description: 'Hosts documentation, guides, and knowledge articles — the wisdom of the Complete Automate ecosystem.',
    icon: <MenuBookRoundedIcon sx={{ fontSize: 36 }} />,
    tech: ['Python', 'FastAPI', 'Markdown'],
  },
  {
    name: 'Atlas',
    god: 'Ἄτλας — Titan who held up the Heavens',
    myth: 'Condemned to hold the celestial sphere on his shoulders for eternity.',
    function: 'S3 File Storage',
    description: 'Provides file upload, serving, and management. The backbone that holds up all media assets — images, documents, and uploads.',
    icon: <CloudQueueRoundedIcon sx={{ fontSize: 36 }} />,
    tech: ['Python', 'FastAPI', 'S3'],
  },
  {
    name: 'Clio',
    god: 'Κλειώ — Muse of History',
    myth: 'One of the nine Muses — keeper of history and recorder of great deeds.',
    function: 'DynamoDB Persistence',
    description: 'Database layer providing structured data persistence. Records all historical data — messages, leads, and business records.',
    icon: <StorageRoundedIcon sx={{ fontSize: 36 }} />,
    tech: ['Python', 'FastAPI', 'DynamoDB'],
  },
  {
    name: 'Helios',
    god: 'Ἥλιος — Titan of the Sun',
    myth: 'Drove the sun chariot across the sky each day, illuminating all below.',
    function: 'Admin Dashboard (Frontend)',
    description: 'The React-based admin UI that brings light to the entire system — dashboards, service health, bookmarks, and management panels.',
    icon: <DashboardRoundedIcon sx={{ fontSize: 36 }} />,
    tech: ['React', 'MUI', 'TypeScript'],
  },
  {
    name: 'Hestia',
    god: 'Ἑστία — Goddess of the Hearth',
    myth: 'Keeper of the sacred hearth fire around which all of Olympus gathered.',
    function: 'Backend API Gateway',
    description: 'The central API gateway and service health monitor — the hearth fire that connects and coordinates all microservices.',
    icon: <ApiRoundedIcon sx={{ fontSize: 36 }} />,
    tech: ['Python', 'FastAPI', 'k8s'],
  },
  {
    name: 'Iris',
    god: 'Ἶρις — Goddess of Messages & Rainbow',
    myth: 'Messenger of the gods who travelled the rainbow bridge between worlds.',
    function: 'Email Delivery',
    description: 'Handles outbound email delivery — transactional emails, notifications, and automated correspondence.',
    icon: <SendRoundedIcon sx={{ fontSize: 36 }} />,
    tech: ['Python', 'FastAPI', 'SMTP'],
  },
  {
    name: 'Orpheus',
    god: 'Ὀρφεύς — Musician who Charmed All',
    myth: 'Legendary musician whose lyre could charm rocks, rivers, and even Hades.',
    function: 'YouTube Content Processing',
    description: 'Downloads, processes, and manages YouTube video content — transcribing, summarizing, and cataloguing like a digital lyre.',
    icon: <SlideshowRoundedIcon sx={{ fontSize: 36 }} />,
    tech: ['Python', 'yt-dlp', 'FFmpeg'],
  },
  {
    name: 'Pythia',
    god: 'Πυθία — Oracle of Delphi',
    myth: 'High priestess who delivered prophecies from Apollo at the Temple of Delphi.',
    function: 'AI / LLM Oracle',
    description: 'Provides AI-powered insights, predictions, and language model responses — the oracle of the microservices ecosystem.',
    icon: <PsychologyRoundedIcon sx={{ fontSize: 36 }} />,
    tech: ['Python', 'FastAPI', 'LLM'],
  },
];

export default function ServicesOverviewPage() {
  return (
    <Box sx={{ p: 1 }}>
      <Typography variant="h4" sx={{ mb: 0.5, fontWeight: 700 }}>
        Micro‑Army Architecture
      </Typography>
      <Typography variant="body2" sx={{ mb: 1, color: 'text.secondary' }}>
        All services run on the <strong>Olympus</strong> k3s cluster, named after the home of the Greek gods.
        Each service is named after a figure from Greek mythology whose domain mirrors its function.
      </Typography>
      <Typography variant="caption" sx={{ mb: 4, display: 'block', color: 'text.secondary' }}>
        <code>microservices</code> namespace &middot; Internal DNS: <code>&lt;name&gt;.microservices.svc.cluster.local:8000</code>
      </Typography>

      <Grid container spacing={2}>
        {services.map((svc) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={svc.name}>
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
              <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 1.5 }}>
                  <Box sx={{ color: 'primary.main', lineHeight: 0, mt: 0.5 }}>
                    {svc.icon}
                  </Box>
                  <Box sx={{ flexGrow: 1 }}>
                    <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.1rem', lineHeight: 1.2 }}>
                      {svc.name}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'primary.main', display: 'block', mt: 0.25 }}>
                      {svc.god}
                    </Typography>
                  </Box>
                </Box>

                <Typography
                  variant="subtitle2"
                  sx={{ fontWeight: 600, mb: 0.5, color: 'secondary.main' }}
                >
                  {svc.function}
                </Typography>

                <Typography variant="body2" sx={{ color: 'text.secondary', mb: 1.5, lineHeight: 1.5 }}>
                  {svc.description}
                </Typography>

                <Typography
                  variant="caption"
                  sx={{ color: 'text.secondary', display: 'block', mb: 0.75, fontStyle: 'italic' }}
                >
                  {svc.myth}
                </Typography>

                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {svc.tech.map((t) => (
                    <Chip
                      key={t}
                      label={t}
                      size="small"
                      variant="outlined"
                      sx={{ height: 20, fontSize: '0.7rem' }}
                    />
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
