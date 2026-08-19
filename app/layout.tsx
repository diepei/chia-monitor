import type {Metadata,Viewport} from "next"; import "./globals.css"; import {RegisterServiceWorker} from "./register-sw";
export const metadata:Metadata={title:"Chia Monitor — Farm health at a glance",description:"A private, lightweight health dashboard for your Chia farm.",applicationName:"Chia Monitor",manifest:"/manifest.webmanifest",appleWebApp:{capable:true,statusBarStyle:"black-translucent",title:"Chia Monitor"}};
export const viewport:Viewport={themeColor:"#07110d",width:"device-width",initialScale:1,viewportFit:"cover"};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="en"><body><RegisterServiceWorker/>{children}</body></html>}
