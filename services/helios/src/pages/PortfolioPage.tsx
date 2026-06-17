import { usePortfolio } from '../hooks/usePortfolio';

import { DataGrid, GridColDef } from '@mui/x-data-grid';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value);
}

function formatPct(value: number): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

const columns: GridColDef[] = [
  {
    field: 'ticker',
    headerName: 'Ticker',
    width: 100,
    renderCell: (params) => (
      <Typography fontWeight={600}>{params.value}</Typography>
    ),
  },
  { field: 'name', headerName: 'Company', width: 220 },
  {
    field: 'shares',
    headerName: 'Shares',
    width: 100,
    type: 'number',
  },
  {
    field: 'price',
    headerName: 'Price',
    width: 120,
    type: 'number',
    valueFormatter: (value: number) => formatCurrency(value),
  },
  {
    field: 'change_pct',
    headerName: 'Change %',
    width: 120,
    renderCell: (params) => {
      const val = params.value as number;
      return (
        <Typography color={val >= 0 ? 'success.main' : 'error.main'}>
          {formatPct(val)}
        </Typography>
      );
    },
  },
  {
    field: 'change_dollar',
    headerName: 'Change $',
    width: 120,
    renderCell: (params) => {
      const val = params.value as number;
      return (
        <Typography color={val >= 0 ? 'success.main' : 'error.main'}>
          {formatCurrency(val)}
        </Typography>
      );
    },
  },
  {
    field: 'total_value',
    headerName: 'Total Value',
    width: 140,
    type: 'number',
    valueFormatter: (value: number) => formatCurrency(value),
  },
  {
    field: 'total_pnl',
    headerName: 'P&L',
    width: 120,
    renderCell: (params) => {
      const val = params.value as number;
      return (
        <Typography color={val >= 0 ? 'success.main' : 'error.main'} fontWeight={600}>
          {formatCurrency(val)}
        </Typography>
      );
    },
  },
];

export function PortfolioPage() {
  const { data, loading, error, refresh } = usePortfolio();

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Portfolio
      </Typography>

      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}

      {/* Summary cards */}
      {data && (
        <Stack direction="row" spacing={3} sx={{ mb: 3 }}>
          <Card sx={{ minWidth: 200 }}>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                Total Value
              </Typography>
              <Typography variant="h5">{formatCurrency(data.total_value)}</Typography>
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200 }}>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                Today's P&L
              </Typography>
              <Typography
                variant="h5"
                color={data.total_pnl >= 0 ? 'success.main' : 'error.main'}
              >
                {formatCurrency(data.total_pnl)}
              </Typography>
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200 }}>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                Market
              </Typography>
              <Typography variant="h5">
                {data.market_open === null
                  ? '—'
                  : data.market_open
                    ? '🟢 Open'
                    : '🔴 Closed'}
              </Typography>
            </CardContent>
          </Card>
        </Stack>
      )}

      {/* Table */}
      <Card>
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="subtitle2" color="text.secondary">
            {data ? `Updated ${new Date(data.updated_at).toLocaleTimeString()}` : 'Loading…'}
          </Typography>
          <Button
            size="small"
            startIcon={<RefreshRoundedIcon />}
            onClick={refresh}
            disabled={loading}
          >
            Refresh
          </Button>
        </Box>
        <DataGrid
          rows={data?.holdings ?? []}
          columns={columns}
          getRowId={(row) => row.ticker}
          loading={loading}
          autoHeight
          disableRowSelectionOnClick
          sx={{ border: 'none' }}
        />
      </Card>
    </Box>
  );
}
