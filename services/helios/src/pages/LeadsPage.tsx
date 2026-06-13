import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import { useNavigate } from 'react-router-dom';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useHeliosData } from '../context/HeliosDataContext';
import { formatTime } from '../lib/helios';
import type { Lead } from '../lib/types';

function ScoreChip({ score }: { score: number }) {
  const color = score >= 8 ? 'success' : score >= 5 ? 'warning' : 'default';
  return <Chip label={`${score}/10`} color={color} size="small" variant="outlined" />;
}

function StateChip({ state }: { state: string }) {
  const colorMap: Record<string, 'info' | 'primary' | 'success' | 'warning' | 'default'> = {
    discovery: 'info',
    contacted: 'primary',
    qualified: 'success',
    won: 'warning',
    not_interested: 'default',
  };
  return <Chip label={state} color={colorMap[state] || 'default'} size="small" />;
}

export function LeadsPage() {
  const navigate = useNavigate();
  const { leads, leadLoading, leadError, fetchLeads } = useHeliosData();

  const columns: GridColDef[] = [
    { field: 'source', headerName: 'Source', width: 100 },
    {
      field: 'company',
      headerName: 'Company',
      width: 200,
      renderCell: (params) => (
        <Typography variant="body2" fontWeight={500} noWrap>
          {params.value}
        </Typography>
      ),
    },
    {
      field: 'score',
      headerName: 'Score',
      width: 100,
      renderCell: (params) => <ScoreChip score={params.value} />,
    },
    {
      field: 'state',
      headerName: 'State',
      width: 130,
      renderCell: (params) => <StateChip state={params.value} />,
    },
    {
      field: 'urgency',
      headerName: 'Urgency',
      width: 100,
      renderCell: (params) => (
        <Chip label={params.value} size="small" variant="outlined" />
      ),
    },
    { field: 'pain_point', headerName: 'Pain Point', width: 350 },
    {
      field: 'seen_at',
      headerName: 'Seen',
      width: 100,
      renderCell: (params) => (
        <Typography variant="caption">{formatTime(params.value)}</Typography>
      ),
    },
  ];

  const rows = leads.map((l: Lead) => ({
    id: l.id,
    source: l.source,
    company: l.company || l.title,
    score: l.score,
    state: l.state,
    urgency: l.urgency,
    pain_point: l.pain_point,
    seen_at: l.seen_at,
  }));

  return (
    <Box sx={{ width: '100%' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography component="h2" variant="h6">
          Pipeline
        </Typography>
        <Button
          variant="outlined"
          size="small"
          startIcon={<RefreshRoundedIcon />}
          onClick={fetchLeads}
        >
          Refresh
        </Button>
      </Stack>
      {leadError && (
        <Typography color="error" sx={{ mb: 2 }}>
          {leadError}
        </Typography>
      )}
      <DataGrid
        rows={rows}
        columns={columns}
        loading={leadLoading}
        density="compact"
        initialState={{ pagination: { paginationModel: { pageSize: 20 } } }}
        pageSizeOptions={[10, 20, 50]}
        onRowClick={(params) => navigate(`/leads/${params.id}`)}
        sx={{ cursor: 'pointer' }}
        autoHeight
      />
    </Box>
  );
}
