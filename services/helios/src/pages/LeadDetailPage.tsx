import { useNavigate, useParams } from 'react-router-dom';
import { useEffect } from 'react';
import { useHeliosData } from '../context/HeliosDataContext';
import { LEAD_STATES, formatDate, formatTime } from '../lib/helios';
import type { Lead } from '../lib/types';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Grid from '@mui/material/Grid';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded';
import OpenInNewRoundedIcon from '@mui/icons-material/OpenInNewRounded';

function EnrichmentField({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {label}:
      </Typography>{' '}
      <Typography variant="body2">{value}</Typography>
    </Box>
  );
}

function LinkField({ label, href }: { label: string; href: string | null }) {
  if (!href) return null;
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {label}:
      </Typography>{' '}
      <Button
        variant="text"
        size="small"
        href={href}
        target="_blank"
        endIcon={<OpenInNewRoundedIcon fontSize="small" />}
        sx={{ textTransform: 'none', p: 0, minWidth: 0 }}
      >
        {href.replace(/^https?:\/\//, '').split('/')[0]}
      </Button>
    </Box>
  );
}

export function LeadDetailPage() {
  const navigate = useNavigate();
  const { leadId } = useParams();
  const { leads, leadDetail, detailLoading, fetchLeadDetail, updateState } = useHeliosData();

  useEffect(() => {
    if (leadId) fetchLeadDetail(leadId);
  }, [fetchLeadDetail, leadId]);

  const lead: Lead | null =
    leadDetail?.id === leadId
      ? leadDetail
      : leads.find((l: Lead) => l.id === leadId) ?? null;

  if (detailLoading) {
    return (
      <Box sx={{ py: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">Loading lead details…</Typography>
      </Box>
    );
  }

  if (!lead) {
    return (
      <Box sx={{ py: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">Lead not found.</Typography>
        <Button onClick={() => navigate('/leads')} sx={{ mt: 2 }}>
          Back to Pipeline
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 900 }}>
      <Button
        startIcon={<ArrowBackRoundedIcon />}
        onClick={() => navigate('/leads')}
        sx={{ mb: 2, color: 'text.secondary' }}
      >
        Leads
      </Button>

      {/* Header Card */}
      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
            <Box>
              <Stack direction="row" gap={1} alignItems="center">
                <Typography variant="h5" fontWeight={700}>
                  {lead.company || lead.title}
                </Typography>
                <Chip label={lead.source} size="small" variant="outlined" />
              </Stack>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                {formatTime(lead.seen_at)} · {formatDate(lead.seen_at)}
              </Typography>
            </Box>
            <Stack direction="row" gap={1}>
              <Chip label={lead.state} size="small" />
              <Chip label={`${lead.score}/10`} size="small" />
              <Chip label={lead.urgency} size="small" variant="outlined" />
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {/* State Changer */}
      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>
            Change State
          </Typography>
          <ToggleButtonGroup
            value={lead.state}
            exclusive
            onChange={(_, newState) => {
              if (newState) updateState(lead.id, newState);
            }}
            size="small"
          >
            {LEAD_STATES.map((state) => (
              <ToggleButton key={state} value={state}>
                {state}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </CardContent>
      </Card>

      {/* Pain Point & Fit */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>
                Pain Point
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {lead.pain_point}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>
                Fit Reason
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {lead.fit_reason}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Angle */}
      {lead.angle && (
        <Card variant="outlined" sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>
              Suggested Angle
            </Typography>
            <Typography variant="body2" fontStyle="italic" color="text.secondary">
              {lead.angle}
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* Enrichment */}
      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" alignItems="center" gap={1} sx={{ mb: 2 }}>
            <Typography variant="subtitle2">Enrichment</Typography>
            <Chip
              label={lead.enriched_at ? 'Enriched' : 'None yet'}
              color={lead.enriched_at ? 'success' : 'default'}
              size="small"
            />
          </Stack>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <LinkField label="Website" href={lead.website} />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <LinkField label="LinkedIn" href={lead.linkedin} />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <EnrichmentField
                label="Contact"
                value={
                  lead.contact_name
                    ? `${lead.contact_name}${lead.contact_email ? ` (${lead.contact_email})` : ''}`
                    : null
                }
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <EnrichmentField label="Funding" value={lead.funding} />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              {lead.budget_min != null && (
                <EnrichmentField
                  label="Budget"
                  value={`$${lead.budget_min.toLocaleString()}${lead.budget_max ? ` – $${lead.budget_max.toLocaleString()}` : ''} (${lead.budget_confidence || 'unknown'})`}
                />
              )}
            </Grid>
            <Grid size={12}>
              {lead.tech_stack.length > 0 && (
                <EnrichmentField label="Tech Stack" value={lead.tech_stack.join(', ')} />
              )}
            </Grid>
            {lead.recent_news.length > 0 && (
              <Grid size={12}>
                <Typography variant="caption" color="text.secondary">
                  Recent News:
                </Typography>
                <ul style={{ margin: '4px 0 0', paddingLeft: 20 }}>
                  {lead.recent_news.slice(0, 5).map((item) => (
                    <li key={item}>
                      <Typography variant="body2" noWrap>
                        {item}
                      </Typography>
                    </li>
                  ))}
                </ul>
              </Grid>
            )}
          </Grid>
        </CardContent>
      </Card>

      {/* State History */}
      {lead.history.length > 1 && (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>
              State History
            </Typography>
            <Stack gap={1}>
              {lead.history.map((h) => (
                <Stack key={`${h.state}-${h.at}`} direction="row" gap={2} alignItems="center">
                  <Chip label={h.state} size="small" />
                  <Typography variant="caption" color="text.secondary">
                    {formatDate(h.at)}
                  </Typography>
                </Stack>
              ))}
            </Stack>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
