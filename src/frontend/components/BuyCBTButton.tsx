import React from 'react';
import axios from 'axios';

export default function BuyCBTButton({ packSku }: { packSku: 'PACK_20' | 'PACK_60' }) {
  const handleBuy = async () => {
    try {
      const res = await axios.post('/codebot/api/_internal/billing/credits/checkout', { packSku });
      if (res.data && res.data.url) window.location.href = res.data.url;
      else alert('Unable to start checkout. Please try again later.')
    } catch (e:any) {
      console.error('checkout error', e)
      alert('Unable to start checkout. Please try again later.')
    }
  };
  return (
    <button onClick={handleBuy} className="px-4 py-2 bg-blue-700 text-white rounded font-bold hover:bg-blue-800">
      Buy {packSku === 'PACK_20' ? '10,000' : '30,000'} CodeBot Tokens (${packSku === 'PACK_20' ? '20' : '60'})
    </button>
  );
}
