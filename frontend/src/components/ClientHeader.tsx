import { useState } from "react";
import { useAppData } from "../data/store";
import { useOutsideClick } from "../lib/hooks";
import { Building, Check, ChevronDown } from "./ui/icons";
import { RunControl } from "./RunControl";

function ClientSelector({ name, kvk }: { name: string; kvk: string }) {
  const [open, setOpen] = useState(false);
  const ref = useOutsideClick<HTMLDivElement>(() => setOpen(false), open);
  return (
    <div className="client-select" ref={ref}>
      <button
        type="button"
        className="client-select__button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <span className="client-select__icon">
          <Building size={18} />
        </span>
        <span className="client-select__text">
          <span className="client-select__name">{name}</span>
          <span className="client-select__meta">KvK {kvk}</span>
        </span>
        <ChevronDown size={16} className="client-select__chev" />
      </button>
      {open && (
        <div className="client-select__menu" role="menu">
          <div className="client-select__label">Client books</div>
          <button type="button" className="client-select__item is-active" role="menuitemradio" aria-checked="true">
            <span>{name}</span>
            <Check size={15} />
          </button>
          <div className="client-select__hint">One client connected. Multi-client view is available on the firm plan.</div>
        </div>
      )}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="fact">
      <span className="fact__k">{label}</span>
      <span className="fact__v">{value}</span>
    </div>
  );
}

export function ClientHeader() {
  const { customer } = useAppData();

  return (
    <header className="appheader">
      <div className="topbar">
        <div className="brandmark">
          <span className="brandmark__logo" aria-hidden="true">
            AGL
          </span>
          <span className="brandmark__text">
            <span className="brandmark__name">Accountant Console</span>
            <span className="brandmark__sub">Categorisation &amp; reconciliation</span>
          </span>
        </div>
        {customer && <ClientSelector name={customer.name} kvk={customer.kvk} />}
        <div className="topbar__spacer" />
        <RunControl />
      </div>
      {customer && (
        <div className="clientstrip">
          <Fact label="Owner (DGA)" value={customer.owner} />
          <Fact label="VAT scheme" value={`${customer.vat_rate} · ${customer.vat_filing}`} />
          <Fact label="Fiscal period" value={customer.fiscal_period} />
          <Fact label="Seat" value={`${customer.city}, ${customer.country}`} />
          <Fact label="Profile" value={`${customer.industry} · ${customer.headcount} staff`} />
        </div>
      )}
    </header>
  );
}
