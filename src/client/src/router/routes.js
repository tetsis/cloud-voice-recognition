import DashboardLayout from "@/layout/dashboard/DashboardLayout.vue";
// GeneralViews
import NotFound from "@/pages/NotFoundPage.vue";

// Admin pages

// Content pages
import AWS from "@/pages/AWS.vue";
import GCP from "@/pages/GCP.vue";
import Azure from "@/pages/Azure.vue";

const routes = [
  {
    path: "/",
    component: DashboardLayout,
    redirect: "/aws",
    children: [
      {
        path: "aws",
        name: "aws",
        component: AWS
      },
      {
        path: "gcp",
        name: "gcp",
        component: GCP
      },
      {
        path: "azure",
        name: "azure",
        component: Azure
      }
    ]
  },
  { path: "*", component: NotFound }
];

/**
 * Asynchronously load view (Webpack Lazy loading compatible)
 * The specified component must be inside the Views folder
 * @param  {string} name  the filename (basename) of the view to load.
function view(name) {
   var res= require('../components/Dashboard/Views/' + name + '.vue');
   return res;
};**/

export default routes;
