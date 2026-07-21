import '../css/app.css';
import { createInertiaApp } from '@inertiajs/react';
import { createRoot } from 'react-dom/client';
import type { ComponentType, ReactNode } from 'react';
import DashboardLayout from './layouts/DashboardLayout';

const pages = import.meta.glob<{ default: ComponentType & { layout?: (page: React.ReactNode) => React.ReactNode } }>('./pages/**/*.tsx');

createInertiaApp({
    title: (title) => (title ? `${title} · LifeStats` : 'LifeStats'),
    resolve: async (name) => {
        const loader = pages[`./pages/${name}.tsx`];
        if (!loader) throw new Error(`Inertia page not found: ${name}`);
        const module = await loader();
        if (name.startsWith('Dashboard/') && !module.default.layout) {
            module.default.layout = (page: ReactNode) => <DashboardLayout>{page}</DashboardLayout>;
        }
        return module.default;
    },
    setup({ el, App, props }) {
        createRoot(el).render(<App {...props} />);
    },
    progress: { color: '#327b63', showSpinner: false },
});
