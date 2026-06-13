import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import StatCard from './StatCard';
import { useHeliosData } from '../context/HeliosDataContext';

export default function MainGrid() {
  const { messages, leads, unreadCount, hotCount, warmCount } = useHeliosData();

  const statCards = [
    {
      title: 'Total Messages',
      value: String(messages.length),
      interval: 'All time',
      trend: 'neutral' as const,
      data: [messages.length, unreadCount],
    },
    {
      title: 'Unread Inbox',
      value: String(unreadCount),
      interval: 'Needs attention',
      trend: unreadCount > 0 ? ('up' as const) : ('neutral' as const),
      data: [unreadCount, 0],
    },
    {
      title: 'Lead Pipeline',
      value: String(leads.length),
      interval: 'Total prospects',
      trend: 'neutral' as const,
      data: [leads.length, hotCount],
    },
    {
      title: 'Hot Leads',
      value: String(hotCount),
      interval: 'Score ≥ 8',
      trend: hotCount > 0 ? ('up' as const) : ('neutral' as const),
      data: [hotCount, 0],
    },
    {
      title: 'Warm Leads',
      value: String(warmCount),
      interval: 'Score 5-7',
      trend: warmCount > 0 ? ('up' as const) : ('neutral' as const),
      data: [warmCount, 0],
    },
  ];

  return (
    <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
      <Typography component="h2" variant="h6" sx={{ mb: 2 }}>
        Overview
      </Typography>
      <Grid container spacing={2} columns={12} sx={{ mb: (theme) => theme.spacing(2) }}>
        {statCards.map((card, index) => (
          <Grid key={index} size={{ xs: 12, sm: 6, lg: 3 }}>
            <StatCard {...card} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
