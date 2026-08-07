// Emplacement du logo — marque-lettre "OP" en attendant un vrai logo (ex.
// public/logo.svg). Pour brancher une image réelle plus tard, remplacer le
// contenu de .logo-mark par <img src="/logo.svg" alt="" /> sans toucher au
// reste de la mise en page (taille/espacement déjà gérés par le CSS).
export function Logo() {
  return (
    <div className="brand">
      <span className="logo-mark" aria-hidden="true">
        OP
      </span>
      <span className="brand-text">
        <span className="brand-name">OptiProcure</span>
        <span className="brand-subtitle">Back-office</span>
      </span>
    </div>
  );
}
