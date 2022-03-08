// Copyright (c) 2021 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Subject } from 'rxjs';
import { environment } from 'src/environments/environment';
import { ErrorComponent } from '../error/error.component';
import { FullModel } from '../import-model/import-model.component';

@Injectable({
  providedIn: 'root'
})
export class ModelService {

  baseUrl = environment.baseUrl;
  myModels = [];
  workspacePath: string;
  projectCount = 0;

  projectCreated$: Subject<boolean> = new Subject<boolean>();
  datasetCreated$: Subject<boolean> = new Subject<boolean>();
  optimizationCreated$: Subject<boolean> = new Subject<boolean>();
  benchmarkCreated$: Subject<boolean> = new Subject<boolean>();
  projectChanged$: Subject<{}> = new Subject<{}>();

  token;
  systemInfo = {};

  constructor(
    private http: HttpClient,
    public dialog: MatDialog
  ) { }

  getToken(): string {
    return this.token;
  }

  setToken(token: string) {
    this.token = token;
  }

  setWorkspacePath(path: string) {
    this.workspacePath = path;
    return this.http.post(
      this.baseUrl + 'api/set_workspace',
      { path: path }
    );
  }

  getSystemInfo() {
    this.http.get(
      this.baseUrl + 'api/system_info'
    ).subscribe(
      resp => {
        this.systemInfo = resp;
      },
      error => {
        this.openErrorDialog(error);
      }
    );
  }

  getDefaultPath(name: string) {
    return this.http.post(
      this.baseUrl + 'api/get_default_path',
      { name: name }
    );
  }

  getModelGraph(path: string, groups?: string[]) {
    let groupsParam = '';
    if (groups) {
      groups.forEach(group => {
        groupsParam += '&group=' + group;
      });
    }
    return this.http.get(
      this.baseUrl + 'api/model/graph' + '?path=' + path + groupsParam
    );
  }

  getDictionary(param: string) {
    return this.http.get(this.baseUrl + 'api/dict/' + param);
  }

  getDictionaryWithParam(path: string, paramName: string, param: {}) {
    return this.http.post(this.baseUrl + 'api/dict/' + path + '/' + paramName, param);
  }

  getPossibleValues(param: string, config?: {}) {
    return this.http.post(
      this.baseUrl + 'api/get_possible_values',
      {
        param: param,
        config: config
      }
    );
  }

  getAllModels() {
    return this.http.post(
      this.baseUrl + 'api/get_workloads_list',
      { workspace_path: this.workspacePath }
    );
  }

  getProfile(newModel, modelType: 'optimized_model' | 'input_model') {
    return this.http.post(
      this.baseUrl + 'api/profile',
      {
        id: newModel.id,
        model_path: newModel.model_path,
        model_type: modelType
      }
    );
  }

  getConfiguration(newModel: NewModel) {
    return this.http.post(
      this.baseUrl + 'api/configuration',
      {
        id: newModel.id,
        model_path: newModel.model_path,
        domain: newModel.domain,
        domain_flavour: newModel.domain_flavour
      });
  }

  optimize(newModel: NewModel) {
    return this.http.post(
      this.baseUrl + 'api/optimize',
      {
        workspace_path: this.workspacePath,
        id: newModel.id
      }
    );
  }

  saveWorkload(fullModel: FullModel | {}) {
    fullModel['workspace_path'] = this.workspacePath;
    return this.http.post(
      this.baseUrl + 'api/save_workload',
      fullModel
    );
  }

  saveExampleWorkload(fullModel: FullModel | {}) {
    fullModel['workspace_path'] = this.workspacePath;
    return this.http.post(
      this.baseUrl + 'api/save_example_workload',
      fullModel
    );
  }

  getFileSystem(path: string, filter: FileBrowserFilter) {
    if (filter === 'all') {
      return this.http.get(this.baseUrl + 'api/filesystem', {
        params: {
          path: path + '/'
        }
      });
    }
    return this.http.get(this.baseUrl + 'api/filesystem', {
      params: {
        path: path + '/',
        filter: filter
      }
    });
  }

  listModelZoo() {
    return this.http.get(this.baseUrl + 'api/list_model_zoo');
  }

  getProjectList() {
    return this.http.get(this.baseUrl + 'api/project/list');
  }

  getProjectDetails(id) {
    return this.http.post(this.baseUrl + 'api/project', { id: id });
  }

  createProject(newProject) {
    return this.http.post(this.baseUrl + 'api/project/create',
      newProject
    );
  }

  getDatasetList(id) {
    return this.http.post(this.baseUrl + 'api/dataset/list', { project_id: id });
  }

  getDatasetDetails(id) {
    return this.http.post(this.baseUrl + 'api/dataset', { id: id });
  }

  addDataset(dataset) {
    return this.http.post(this.baseUrl + 'api/dataset/add', dataset);
  }

  getOptimizationList(id) {
    return this.http.post(this.baseUrl + 'api/optimization/list', { project_id: id });
  }

  getOptimizationDetails(id) {
    return this.http.post(this.baseUrl + 'api/optimization', { id: id });
  }

  addOptimization(optimization) {
    return this.http.post(this.baseUrl + 'api/optimization/add', optimization);
  }

  executeOptimization(optimizationId, requestId) {
    return this.http.post(
      this.baseUrl + 'api/optimization/execute',
      {
        request_id: requestId,
        optimization_id: optimizationId,
      }
    );
  }

  addNotes(id, notes) {
    return this.http.post(this.baseUrl + 'api/project/note', {
      id: id,
      notes: notes
    });
  }

  getModelList(id) {
    return this.http.post(this.baseUrl + 'api/model/list', { project_id: id });
  }

  getBenchmarksList(id) {
    return this.http.post(this.baseUrl + 'api/benchmark/list', { project_id: id });
  }

  addBenchmark(benchmark) {
    return this.http.post(this.baseUrl + 'api/benchmark/add', benchmark);
  }

  getBenchmarkDetails(id) {
    return this.http.post(this.baseUrl + 'api/benchmark', { id: id });
  }

  executeBenchmark(benchmarkId, requestId) {
    return this.http.post(
      this.baseUrl + 'api/benchmark/execute',
      {
        request_id: requestId,
        benchmark_id: benchmarkId,
      }
    );
  }

  addProfiling(profiling) {
    return this.http.post(this.baseUrl + 'api/profiling/add', profiling);
  }

  getProfilingList(id) {
    return this.http.post(this.baseUrl + 'api/profiling/list', { project_id: id });
  }

  getProfilingDetails(id) {
    return this.http.post(this.baseUrl + 'api/profiling', { id: id });
  }

  executeProfiling(profilingId, requestId) {
    return this.http.post(
      this.baseUrl + 'api/profiling/execute',
      {
        profiling_id: profilingId,
        request_id: requestId,
      }
    );
  }

  openErrorDialog(error) {
    const dialogRef = this.dialog.open(ErrorComponent, {
      data: error
    });
  }
}

export interface NewModel {
  domain: string;
  domain_flavour: string;
  framework: string;
  id: string;
  input?: string;
  model_path: string;
  output?: string;
}

export type FileBrowserFilter = 'models' | 'datasets' | 'directories' | 'all';
