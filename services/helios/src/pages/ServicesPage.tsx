import { useCallback, useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import { API_BASE } from '../lib/helios';

interface ServiceStatus {
  name: string;
  status: 'up' | 'down' | 'error';
  latency_ms: number | null;
  error: string | null;
  url: string;
  response_status: number | null;
  checked_at: string;
}

const statusColor = (status: ServiceStatus['status']): 'success' | 'error' | 'warning' => {
  switch (status) {
    case 'up': return 'success';
    case 'down': return 'error';
    case 'error': return 'warning';
  }
};

const statusDot = (status: ServiceStatus['status']): string => {
  switch (status) {
    case 'up': return '🟢';
    case 'down': return '🔴';
    case 'error': return '🟡';
  }
};

function formatLatency(ms: number | null): string {
  if (ms === null) return '—';
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function ServiceRow({ service }: { service: ServiceStatus }) {
  return (
    <TableRow
      sx={{
        '&:last-child td, &:last-child th': { border: 0 },
        opacity: service.status === 'up' ? 1 : 0.85,
      }}
    >
      <TableCell component="th" scope="row">
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {statusDot(service.status)}
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {service.name}
          </Typography>
        </Box>
      </TableCell>
      <TableCell>
        <Chip
          size="small"
          color={statusColor(service.status)}
          label={service.status.toUpperCase()}
          variant="outlined"
        />
      </TableCell>
      <TableCell>{formatLatency(service.latency_ms)}</TableCell>
      <TableCell>
        {service.error ? (
          <Typography variant="body2" color="error" sx={{ fontSize: '0.8rem', maxWidth: 300 }}>
            {service.error}
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
            HTTP {service.response_status}
          </Typography>
        )}
      </TableCell>
      <TableCell>
        <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
          {new Date(service.checked_at).toLocaleTimeString()}
        </Typography>
      </TableCell>
    </TableRow>
  );
}

export function ServicesPage() {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStatus = useCallback(async (silent: boolean = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError(null);
    try {
      const resp = await fetch(`${API_BASE}/api/v1/services/status`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setServices(data.services);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load service status');
    }
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => fetchStatus(true), 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const upCount = services.filter((s) => s.status === 'up').length;
  const totalCount = services.length;

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box>
          <Typography component="h2" variant="h6" sx={{ mb: 0.5 }}>
            Service Health
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {upCount} / {totalCount} services healthy
          </Typography>
        </Box>
        <Chip
          label={refreshing ? 'Refreshing…' : 'Auto-refresh 30s'}
          size="small"
          variant="outlined"
          color={refreshing ? 'warning' : 'default'}
          onClick={() => fetchStatus(true)}
          sx={{ cursor: 'pointer' }}
        />
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600 }}>Service</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Latency</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Response</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Checked</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {services.map((service) => (
              <ServiceRow key={service.name} service={service} />
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {services.length === 0 && !error && (
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
          No services returned from the status endpoint.
        </Typography>
      )}
    </Box>
  );
}
