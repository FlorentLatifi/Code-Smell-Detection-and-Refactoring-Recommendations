import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

/**
 * Çfarë shihet kur renderimi hedh një përjashtim.
 *
 * Pa këtë, React e çmonton tërë pemën dhe mbetet një faqe krejt bosh: asnjë
 * mesazh, asnjë buton, asnjë tregues se çfarë ndodhi. Për një mjet që lexon të
 * dhëna nga një server që evoluon veç — një fushë e munguar, një `null` aty ku
 * pritej varg — kjo është gjendje reale, jo teorike.
 *
 * Klasë sepse React nuk ofron ekuivalent me hook: `componentDidCatch` dhe
 * `getDerivedStateFromError` ekzistojnë vetëm këtu.
 */
export class Boundary extends Component<{ children: ReactNode }, { failed: Error | null }> {
  state: { failed: Error | null } = { failed: null };

  static getDerivedStateFromError(failed: Error): { failed: Error } {
    return { failed };
  }

  componentDidCatch(failed: Error, info: ErrorInfo): void {
    // Konsola është e vetmja rrugë këtu: nuk ka shërbim raportimi, dhe një mjet
    // që dërgon gjurmë diku pa u pyetur do të ishte gjëja e fundit që kjo depo
    // do të pranonte. Zhvilluesi që e hap konsolën e gjen; askush tjetër nuk e sheh.
    console.error("Renderimi dështoi:", failed, info.componentStack);
  }

  render(): ReactNode {
    const { failed } = this.state;
    if (!failed) return this.props.children;

    return (
      <div className="page">
        <header>
          <h1>JavaSmell</h1>
        </header>
        <main>
          <p className="failure" role="alert">
            Ndërfaqja u ndal papritur. Kjo është defekt i vetë mjetit, jo i kodit që po
            analizoje.
          </p>
          <p className="empty">
            Rifresko faqen për të rifilluar. Nëse përsëritet, hollësitë teknike janë te
            konsola e shfletuesit.
          </p>
          <p className="caption">
            <code>{failed.message}</code>
          </p>
          <button className="primary" onClick={() => window.location.reload()}>
            Rifresko
          </button>
        </main>
      </div>
    );
  }
}
