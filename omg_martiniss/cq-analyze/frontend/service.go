// Copyright 2017 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package cq_analyze

import (
	"fmt"
	"math"
	"time"

	"infra/appengine/cq-analyze/api/cq_analyze"

	"golang.org/x/net/context"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type cqAnalyzeService struct{}

const testQuery = `
WITH
  test AS (
    SELECT cq_name, first_start_msec, last_start_msec
    FROM plx.google.chrome_infra.cq_attempts.all
    LIMIT 1
  )
  SELECT * FROM test
`

const longCacheTime = time.Hour * 24 * 7
const shortCacheTime = time.Minute * 5

func endOfWeek() time.Time {
	// Truncate to a week always gives us a monday, so add 5 days to get saturday.
	return time.Now().Truncate(time.Hour * 24 * 7).Add(time.Hour * 24 * 5)
}

func parseDates(start, end string) (time.Time, time.Time, error) {
	endT, err := time.Parse("2006-01-02", end)
	if err != nil {
		return time.Time{}, time.Time{}, fmt.Errorf("while parsing end time: %v", err)
	}

	startT, err := time.Parse("2006-01-02", start)
	if err != nil {
		return time.Time{}, time.Time{}, fmt.Errorf("while parsing start time: %v", err)
	}

	return startT, endT, nil
}

func (s *cqAnalyzeService) GetLimitingBuilders(c context.Context, req *cq_analyze.GetLimitingBuildersRequest) (*cq_analyze.GetLimitingBuildersResponse, error) {
	res := &cq_analyze.GetLimitingBuildersResponse{
		Builders: []*cq_analyze.LimitingBuilder{},
	}

	if req.StartDate == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply a start date")
	}
	if req.EndDate == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply an end date")
	}

	start, end, err := parseDates(req.StartDate, req.EndDate)
	if err != nil {
		return nil, status.Errorf(codes.InvalidArgument, "%v", err)
	}

	cacheTime := longCacheTime
	if math.Abs(float64(endOfWeek().Sub(end))) < float64(time.Hour*24*7) {
		cacheTime = shortCacheTime
	}
	if err := runQuery(c, limitingQuery(start, end), &res.Builders, cacheTime); err != nil {
		return nil, err
	}
	return res, nil
}

func (s *cqAnalyzeService) GetCLsForBuilder(c context.Context, req *cq_analyze.GetCLsForBuilderRequest) (*cq_analyze.GetCLsForBuilderResponse, error) {
	if req.Builder == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply a builder")
	}
	if req.StartDate == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply a start date")
	}
	if req.EndDate == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply an end date")
	}

	start, end, err := parseDates(req.StartDate, req.EndDate)
	if err != nil {
		return nil, status.Errorf(codes.InvalidArgument, "%v", err)
	}

	res := &cq_analyze.GetCLsForBuilderResponse{
		Builds: []*cq_analyze.LongBuild{},
	}

	cacheTime := longCacheTime
	if math.Abs(float64(endOfWeek().Sub(end))) < float64(time.Hour*24*7) {
		cacheTime = shortCacheTime
	}
	if err := runQuery(c, longestBuilds(req.Builder, start, end), &res.Builds, cacheTime); err != nil {
		return nil, err
	}
	return res, nil
}

type knownBuilderBQ struct {
	Builder string `json:"builder"`
}

func (s *cqAnalyzeService) GetKnownBuilders(c context.Context, req *cq_analyze.GetKnownBuildersRequest) (*cq_analyze.GetKnownBuildersResponse, error) {
	if req.StartDate == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply a start date")
	}
	if req.EndDate == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply an end date")
	}

	start, end, err := parseDates(req.StartDate, req.EndDate)
	if err != nil {
		return nil, status.Errorf(codes.InvalidArgument, "%v", err)
	}

	res := &cq_analyze.GetKnownBuildersResponse{
		Builders: []string{},
	}

	cacheTime := longCacheTime
	if math.Abs(float64(endOfWeek().Sub(end))) < float64(time.Hour*24*7) {
		cacheTime = shortCacheTime
	}
	bqResp := []*knownBuilderBQ{}
	if err := runQuery(c, knownBuildersQuery(start, end), &bqResp, cacheTime); err != nil {
		return nil, err
	}
	res.Builders = make([]string, len(bqResp))
	for i, s := range bqResp {
		res.Builders[i] = s.Builder
	}
	return res, nil
}

func (s *cqAnalyzeService) GetLongSteps(c context.Context, req *cq_analyze.GetLongStepsRequest) (*cq_analyze.GetLongStepsResponse, error) {
	if req.Builder == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply a builder")
	}
	if req.StartDate == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply a start date")
	}
	if req.EndDate == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply an end date")
	}

	start, end, err := parseDates(req.StartDate, req.EndDate)
	if err != nil {
		return nil, status.Errorf(codes.InvalidArgument, "%v", err)
	}

	res := &cq_analyze.GetLongStepsResponse{
		Steps: []*cq_analyze.LongStep{},
	}

	cacheTime := longCacheTime
	if math.Abs(float64(endOfWeek().Sub(end))) < float64(time.Hour*24*7) {
		cacheTime = shortCacheTime
	}
	if err := runQuery(c, longStepsQuery(req.Builder, start, end), &res.Steps, cacheTime); err != nil {
		return nil, err
	}

	finalSteps := []*cq_analyze.LongStep{}
	for _, step := range res.Steps {
		if step.Name == "steps" {
			continue
		}
		finalSteps = append(finalSteps, step)
	}
	res.Steps = finalSteps
	return res, nil
}

func (s *cqAnalyzeService) GetBuilds(c context.Context, req *cq_analyze.GetBuildsRequest) (*cq_analyze.GetBuildsResponse, error) {
	if req.Builder == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply a builder")
	}
	if req.StartDate == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply a start date")
	}
	if req.EndDate == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply an end date")
	}

	start, end, err := parseDates(req.StartDate, req.EndDate)
	if err != nil {
		return nil, status.Errorf(codes.InvalidArgument, "%v", err)
	}

	res := &cq_analyze.GetBuildsResponse{
		Builds: []*cq_analyze.Build{},
	}

	cacheTime := longCacheTime
	if math.Abs(float64(endOfWeek().Sub(end))) < float64(time.Hour*24*7) {
		cacheTime = shortCacheTime
	}
	if err := runQuery(c, buildsQuery(req.Builder, start, end), &res.Builds, cacheTime); err != nil {
		return nil, err
	}
	return res, nil
}

func (s *cqAnalyzeService) GetCLInfoForBuilder(c context.Context, req *cq_analyze.GetCLInfoForBuilderRequest) (*cq_analyze.GetCLInfoForBuilderResponse, error) {
	if req.Builder == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply a builder")
	}
	if req.Issue == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply an issue")
	}
	if req.Patchset == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply a patchset")
	}
	res := &cq_analyze.GetCLInfoForBuilderResponse{
		Builds: []*cq_analyze.Build{},
	}
	err := runQuery(c, clInfoQuery(req.Builder, req.Issue, req.Patchset), &res.Builds, longCacheTime)
	if err != nil {
		return nil, err
	}
	return res, nil
}

func (s *cqAnalyzeService) GetBuildInfo(c context.Context, req *cq_analyze.GetBuildInfoRequest) (*cq_analyze.GetBuildInfoResponse, error) {
	if req.Builder == "" {
		return nil, status.Errorf(codes.InvalidArgument, "must supply a builder")
	}
	if req.BuildNum == 0 {
		return nil, status.Errorf(codes.InvalidArgument, "must supply a build number")
	}
	res := &cq_analyze.GetBuildInfoResponse{
		Steps: []*cq_analyze.Step{},
	}
	err := runQuery(c, buildInfoQuery(req.Builder, req.BuildNum), &res.Steps, longCacheTime)
	if err != nil {
		return nil, err
	}
	finalSteps := []*cq_analyze.Step{}
	for _, step := range res.Steps {
		if step.Name == "steps" {
			res.Duration = step.Duration
			continue
		}
		finalSteps = append(finalSteps, step)
	}
	res.Steps = finalSteps
	if len(res.Steps) > 0 {
		res.Master = res.Steps[0].Master
	}
	return res, nil
}
