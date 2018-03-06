// Copyright 2017 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package cq_analyze

import (
	"fmt"
	"html/template"
	"net/http"
	"os"
	"time"

	"infra/appengine/cq-analyze/api/cq_analyze"

	"go.chromium.org/gae/service/info"
	"go.chromium.org/luci/appengine/gaeauth/server"
	"go.chromium.org/luci/appengine/gaemiddleware/standard"
	"go.chromium.org/luci/auth/identity"
	"go.chromium.org/luci/common/logging"
	"go.chromium.org/luci/grpc/discovery"
	"go.chromium.org/luci/grpc/prpc"
	"go.chromium.org/luci/server/auth"
	"go.chromium.org/luci/server/router"
	"go.chromium.org/luci/server/templates"
)

const authGroup = "auth-service-access"

func getTemplatePath() string {
	path := "build/es6-bundled/templates"
	if _, err := os.Stat(path); os.IsNotExist(err) {
		return "templates"
	}
	return path
}

var templateBundle = &templates.Bundle{
	Loader:    templates.FileSystemLoader(getTemplatePath()),
	DebugMode: info.IsDevAppServer,
	FuncMap: template.FuncMap{
		"fmtDate": func(date time.Time) string {
			return date.Format("1-2-2006")
		},
	},
}

func pageBase(allowAnon bool) router.MiddlewareChain {
	a := auth.Authenticator{
		Methods: []auth.Method{
			&server.OAuth2Method{Scopes: []string{server.EmailScope}},
			&server.InboundAppIDAuthMethod{},
			server.CookieAuth,
		},
	}
	return standard.Base().Extend(a.GetMiddleware()).Extend(
		templates.WithTemplates(templateBundle),
	).Extend(func(c *router.Context, next router.Handler) {
		w := c.Writer
		var isGoogler bool
		var isAnonymous bool
		var err error
		if userIdentity := auth.CurrentIdentity(c.Context); userIdentity == identity.AnonymousIdentity {
			isAnonymous = true
			isGoogler = false
		} else {
			isAnonymous = false
			isGoogler, err = auth.IsMember(c.Context, authGroup)
			if err != nil {
				logging.Warningf(c.Context, "failed to determine membership status: %v", err)
			}
		}

		if (isAnonymous && !allowAnon) || (!allowAnon && !isGoogler) {
			logoutURL, err := auth.LogoutURL(c.Context, "/")
			if err != nil {
				logging.Errorf(c.Context, "failed to get logout URL: %v", err)
			}
			w.WriteHeader(http.StatusUnauthorized)
			fmt.Fprintf(w, "Unauthorized. Contact infra-dev AT chromium DOT org if you should be able to reach this page. Log out at %v", logoutURL)
			return
		}
		next(c)
	})
}

func dashboard(ctx *router.Context) {
	c, w, r := ctx.Context, ctx.Writer, ctx.Request

	loginURL, err := auth.LoginURL(c, "/")
	if err != nil {
		http.Error(w, "failed to get login URL", http.StatusInternalServerError)
		logging.Errorf(c, "failed to get login URL: %v", err)
		return
	}
	logoutURL, err := auth.LogoutURL(c, "/")
	if err != nil {
		http.Error(w, "failed to get logout URL", http.StatusInternalServerError)
		logging.Errorf(c, "failed to get logout URL: %v", err)
		return
	}

	var isGoogler bool
	var isAnonymous bool
	var user string
	if userIdentity := auth.CurrentIdentity(c); userIdentity == identity.AnonymousIdentity {
		isAnonymous = true
		isGoogler = false
	} else {
		user = userIdentity.Email()
		isAnonymous = false
		isGoogler, err = auth.IsMember(c, authGroup)
		if err != nil {
			http.Error(w, "failed to determine membership status", http.StatusInternalServerError)
			logging.Errorf(c, "failed to determine membership status: %v", err)
			return
		}
	}

	if isAnonymous {
		http.Redirect(w, r, loginURL, http.StatusFound)
		return
	}
	if !isGoogler {
		w.WriteHeader(http.StatusUnauthorized)
		fmt.Fprintf(w, "Unauthorized. Contact infra-dev AT chromium DOT org if you should be able to reach this page. Log out at %v", logoutURL)
		return
	}

	templates.MustRender(c, w, "pages/home.html", templates.Args{
		"IsAnoymous": isAnonymous,
		"User":       user,
		"IsGoogler":  isGoogler,
		"LoginURL":   loginURL,
		"LogoutURL":  logoutURL,
	})
}

func init() {
	r := router.New()
	standard.InstallHandlers(r)
	r.GET("/", pageBase(true), func(ctx *router.Context) {
		http.Redirect(ctx.Writer, ctx.Request, "/app/", 302)
	})
	r.GET("/app/*whatever", pageBase(true), dashboard)

	var api prpc.Server
	cq_analyze.RegisterCQAnalyzeServiceServer(&api, &cqAnalyzeService{})
	discovery.Enable(&api)
	api.InstallHandlers(r, pageBase(false))
	http.DefaultServeMux.Handle("/", r)
}
