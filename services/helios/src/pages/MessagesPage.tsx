import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import { useNavigate } from 'react-router-dom';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import { useHeliosData } from '../context/HeliosDataContext';
import { formatTime, formatDate } from '../lib/helios';
import DeleteRoundedIcon from '@mui/icons-material/DeleteRounded';
import VisibilityOffRoundedIcon from '@mui/icons-material/VisibilityOffRounded';
import type { Message } from '../lib/types';

export function MessagesPage() {
  const navigate = useNavigate();
  const { messages, msgLoading, msgError, fetchMessages, markRead, deleteMessage } = useHeliosData();

  const columns: GridColDef[] = [
    {
      field: 'read',
      headerName: '',
      width: 50,
      renderCell: (params) => (
        <Box
          sx={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            bgcolor: params.value ? 'grey.400' : 'primary.main',
          }}
        />
      ),
    },
    { field: 'name', headerName: 'From', width: 200 },
    { field: 'email', headerName: 'Email', width: 250 },
    { field: 'subject', headerName: 'Subject', width: 300 },
    {
      field: 'created_at',
      headerName: 'Received',
      width: 160,
      renderCell: (params) => (
        <Stack>
          <Typography variant="caption">{formatTime(params.value)}</Typography>
          <Typography variant="caption" color="text.secondary">
            {formatDate(params.value)}
          </Typography>
        </Stack>
      ),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 100,
      getActions: (params) => [
        <GridActionsCellItem
          key="read"
          icon={<VisibilityOffRoundedIcon />}
          label="Mark Read"
          onClick={() => markRead(params.id as string)}
          showInMenu
        />,
        <GridActionsCellItem
          key="delete"
          icon={<DeleteRoundedIcon />}
          label="Delete"
          onClick={() => {
            if (globalThis.confirm(`Delete message from ${params.row.name}?`)) {
              deleteMessage(params.id as string);
            }
          }}
          showInMenu
        />,
      ],
    },
  ];

  const rows = messages.map((m: Message) => ({
    id: m.id,
    name: m.name,
    email: m.email,
    subject: m.subject,
    message: m.message,
    read: m.read,
    created_at: m.created_at,
  }));

  return (
    <Box sx={{ width: '100%' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography component="h2" variant="h6">
          Inbox
        </Typography>
        <Button
          variant="outlined"
          size="small"
          startIcon={<RefreshRoundedIcon />}
          onClick={fetchMessages}
        >
          Refresh
        </Button>
      </Stack>
      {msgError && (
        <Typography color="error" sx={{ mb: 2 }}>
          {msgError}
        </Typography>
      )}
      <DataGrid
        rows={rows}
        columns={columns}
        loading={msgLoading}
        density="compact"
        initialState={{ pagination: { paginationModel: { pageSize: 20 } } }}
        pageSizeOptions={[10, 20, 50]}
        onRowClick={(params) => navigate(`/messages/${params.id}`)}
        sx={{ cursor: 'pointer' }}
        autoHeight
      />
    </Box>
  );
}
