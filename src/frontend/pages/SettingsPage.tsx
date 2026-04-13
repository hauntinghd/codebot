// src/frontend/pages/SettingsPage.tsx
// ...existing imports...
import BuyCBTButton from '../components/BuyCBTButton';

// ...inside your settings or billing section...
<div>
  <h3>Buy Extra CodeBot Tokens</h3>
  <BuyCBTButton packSku="PACK_20" />
  <BuyCBTButton packSku="PACK_60" />
  {/* PRO_250 is coming soon and not shown */}
</div>
