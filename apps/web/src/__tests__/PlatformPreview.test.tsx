import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PlatformPreview } from '../components/common/PlatformPreview';

describe('PlatformPreview Component', () => {
  it('renders LinkedIn preview with hook, body, CTA, and AI disclosure', () => {
    render(
      <PlatformPreview
        platform="linkedin"
        hook="Pourquoi les architectures agentiques échouent en prod"
        body="90% des déploiements sous-estiment la gouvernance humaine et la traçabilité des décisions."
        cta="Lisez notre post-mortem complet en premier commentaire."
        hashtags={['AI', 'AgentOps', 'LangGraph']}
        authorName="Martial - Lead Tech"
        isAiDisclosed={true}
      />
    );

    expect(screen.getByText('Pourquoi les architectures agentiques échouent en prod')).toBeInTheDocument();
    expect(screen.getByText(/90% des déploiements sous-estiment/)).toBeInTheDocument();
    expect(screen.getByText('Lisez notre post-mortem complet en premier commentaire.')).toBeInTheDocument();
    expect(screen.getByText('#AI #AgentOps #LangGraph')).toBeInTheDocument();
    expect(screen.getByText(/Assisté par agent d'IA vérifié par validation humaine/i)).toBeInTheDocument();
    expect(screen.getByText('LinkedIn')).toBeInTheDocument();
  });

  it('renders X preview and alerts when text exceeds 280 characters', () => {
    const longText = 'A'.repeat(290);
    render(
      <PlatformPreview
        platform="x"
        hook="Alerte dépassement"
        body={longText}
        cta="Cliquez ici"
        accountName="analyticatech"
      />
    );

    expect(screen.getByText('X / Post')).toBeInTheDocument();
    expect(screen.getByText(/Dépassement de la limite X de 280 caractères/i)).toBeInTheDocument();
  });

  it('renders X preview without warning when within character limit', () => {
    render(
      <PlatformPreview
        platform="x"
        hook="Court et percutant"
        body="Voici une annonce condensée pour notre communauté."
        cta=""
        accountName="analyticatech"
      />
    );

    expect(screen.getByText('Court et percutant')).toBeInTheDocument();
    expect(screen.queryByText(/Dépassement de la limite X/i)).not.toBeInTheDocument();
  });
});
