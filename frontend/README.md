# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.

## Dependencies

Versions are pinned exactly (`package.json` plus `.npmrc save-exact=true`), the same discipline as the Python lock: the build must resolve identically over time.

`react-router-dom` stays pinned at `7.18.1` despite `npm audit` flagging GHSA-qwww-vcr4-c8h2. That advisory is a CSRF bypass in React Router's RSC / framework-mode server actions; this app is a client-only BrowserRouter SPA with no SSR, no React Server Components, and no server actions, so that code path does not exist here and the advisory does not apply. 7.18.1 is already above every relevant patch, and npm's suggested "fix" downgrades to 7.11.0, which is below them, so the pin stays.
