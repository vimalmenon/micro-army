import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { useNavigate } from 'react-router-dom';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useHeliosData } from '../context/HeliosDataContext';
import MainGrid from '../components/MainGrid';
import { formatTime } from '../lib/helios';
import type { Lead, Message } from '../lib/types';

function RecentMessagesGrid({ messages }: { messages: Message[] }) {
  const navigate = useNavigate();
  const columns: GridColDef[] = [
    { field: 'name', headerName: 'From', width: 180 },
    { field: 'subject', headerName: 'Subject', width: 250 },
    { field: 'created_at', headerName: 'Received', width: 150 },
    { field: 'read', headerName: 'Status', width: 100 },
  ];

  const rows = messages.map((m) => ({
    id: m.id,
    name: m.name,
    subject: m.subject,
    created_at: formatTime(m.created_at),
    read: m.read ? 'Read' : 'Unread',
  }));

  return (
    <Box sx={{ height: 350, width: '100%' }}>
      <DataGrid
        rows={rows}
        columns={columns}
        density="compact"
        hideFooter
        onRowClick={(params) => navigate(`/messages/${params.id}`)}
        sx={{ cursor: 'pointer' }}
      />
    </Box>
  );
}

function RecentLeadsGrid({ leads }: { leads: Lead[] }) {
  const navigate = useNavigate();
  const columns: GridColDef[] = [
    { field: 'company', headerName: 'Company', width: 180 },
    { field: 'score', headerName: 'Score', width: 80 },
    { field: 'urgency', headerName: 'Urgency', width: 100 },
    { field: 'state', headerName: 'State', width: 120 },
    { field: 'pain_point', headerName: 'Pain Point', width: 300 },
  ];

  const rows = leads.map((l) => ({
    id: l.id,
    company: l.company || l.title,
    score: `${l.score}/10`,
    urgency: l.urgency,
    state: l.state,
    pain_point: l.pain_point,
  }));

  return (
    <Box sx={{ height: 350, width: '100%' }}>
      <DataGrid
        rows={rows}
        columns={columns}
        density="compact"
        hideFooter
        onRowClick={(params) => navigate(`/leads/${params.id}`)}
        sx={{ cursor: 'pointer' }}
      />
    </Box>
  );
}

export function DashboardPage() {
  const { messages, leads } = useHeliosData();

  return (
    <>
      <MainGrid />

      <Typography component="h2" variant="h6" sx={{ mb: 2, mt: 4 }}>
        Recent Messages
      </Typography>
      <RecentMessagesGrid messages={messages.slice(0, 5)} />

      <Typography component="h2" variant="h6" sx={{ mb: 2, mt: 4 }}>
        Recent Leads
      </Typography>
      <RecentLeadsGrid leads={leads.slice(0, 6)} />
    </>
  );
}
