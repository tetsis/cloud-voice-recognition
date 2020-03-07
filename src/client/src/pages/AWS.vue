<template>
  <div>

    <!--Card-->
    <div v-show="status == 'upload'" class="row">
      <div class="col-md-12">
        <card :title="card.title" :subTitle="card.subTitle">
          <div>
            <!-- Styled -->
            <b-form-file
              v-model="file"
              :state="Boolean(file)"
              placeholder="Choose a file or drop it here..."
              drop-placeholder="Drop file here..."
            ></b-form-file>
            <div class="mt-3">Selected file: {{ file ? file.name : '' }}</div>
          </div>
          <div class="text-center">
            <p-button type="info"
                      v-bind:disabled="isUpload"
                      round
                      @click.native.prevent="updateFile">
                        <span v-show="!isUpload">Upload voice file</span>
                        <span v-show="isUpload">
                          <b-spinner type="grow"></b-spinner>
                          Uploading...
                        </span>
            </p-button>
          </div>
        </card>
      </div>
    </div>

    <!--Card-->
    <div v-show="status == 'recognize'" class="row">
      <div class="col-md-12">
        <card :title="recognitionCard.title" :subTitle="recognitionCard.subTitle">
          <div class="text-center my-2">
            <b-spinner class="align-middle"></b-spinner>
            <strong>{{ recognize_sentence }}</strong>
          </div>
        </card>
      </div>
    </div>

    <!--Card-->
    <div v-show="status == 'complete'" class="row">
      <div class="col-md-12">
        <card :title="resultCard.title" :subTitle="resultCard.subTitle">
          <div class="text-center my-2">
            <p>{{ transcript }}</p>
          </div>
          <div class="text-center">
            <p-button type="info"
                      round
                      @click.native.prevent="backToUpload">
                        <span>Back to upload</span>
            </p-button>
          </div>
        </card>
      </div>
    </div>

    <!--Card-->
    <div class="row">
      <div class="col-md-12">
        <card :title="historyCard.title" :subTitle="historyCard.subTitle">
          <div>
          <b-table
            ref="historyTable"
            id="gcp-history-table"
            :busy="isBusy"
            :items="myProvider"
          >
          </b-table>
          </div>
        </card>
      </div>
    </div>

  </div>
</template>

<script>
import { StatsCard } from "@/components/index";
import NotificationTemplate from './Notifications/NotificationTemplate';
import axios from 'axios';
export default {
  components: {
    StatsCard,
  },
  data() {
    return {
      now_num: 0,
      histories: {},
      getVoiceTextInterval: null,
      transcript: '',
      recognize_sentence: '  Starting recognition...',
      isBusy: false,
      card: {
        title: "Upload to S3",
      },
      historyCard: {
        title: "History",
      },
      recognitionCard: {
        title: "Recognizing",
        subTitle: ""
      },
      resultCard: {
        title: "Recognition result",
        subTitle: ""
      },
      file: null,
      isUpload: false,
      status: 'upload',
    };
  },
  mounted() {
    if (localStorage.getItem('histories')) {
      try {
        this.histories = JSON.parse(localStorage.getItem('histories'));
      } catch(e) {
        localStorage.removeItem('histories');
      }
    }
  },
  methods: {
    backToUpload() {
      this.status = 'upload';
    },
    myProvider() {
      let items = []
      for (let [key, value] of Object.entries(this.histories)) {
        let object_name = key;
        let status = value['status'];
        let transcript = value['transcript'];
        items.unshift({
          object_name: object_name,
          status: status,
          transcript: transcript
        })
      }
      return items || []
    },
    saveHistories() {
      const parsed = JSON.stringify(this.histories);
      localStorage.setItem('histories', parsed);
      this.$refs.historyTable.refresh()
    },
    notifyVue(verticalAlign, horizontalAlign, type, title) {
      this.$notify({
        title: title,
        horizontalAlign: horizontalAlign,
        verticalAlign: verticalAlign,
        type: type
      });
    },
    updateFile() {
      let formData = new FormData();
      let config = {
        headers: {
          'content-type': 'multipart/form-data'
        }
      };
      formData.append('audio', this.file);
      this.isUpload = true;
      axios
        .post('/api/aws/upload', formData, config)
        .then(response => {
          this.isUpload = false;
          this.file = null;

          let data = response.data;
          this.object_name = data['object_name'];
          console.log(this.object_name);

          // localStorageに保存
          this.histories[this.object_name] = {};
          this.saveHistories();

          console.log('success');
          this.notifyVue('top', 'right', 'success', 'Upload successful')

          this.recognizeVoice();
        })
        .catch(response => {
          this.isUpload = false;
          this.file = null;
          console.log('failed');
        })
    },
    recognizeVoice() {
      let params = new URLSearchParams();
      params.append('object_name', this.object_name);
      this.recognitionCard.subTitle = this.object_name;
      this.resultCard.subTitle = this.object_name;

      this.status = 'recognize';

      axios
        .post('/api/aws/recognize', params)
        .then(response => {
          console.log('success');

          let data = response.data;
          this.job_name = data['job_name'];
          let status = data['status'];
          this.histories[this.object_name] = {
            'job_name': this.job_name,
            'status': status
          };
          this.saveHistories();
          if (status == 'FAILED') {
            console.log('Failed to recognize');
            this.notifyVue('top', 'right', 'danger', 'Failed to start recognition process')
            this.status = 'upload';
          }
          console.log(this.job_name);

          this.recognize_sentence = '  Recognizing... This process takes a few minutues. Don\'t reload this page.';
          this.notifyVue('top', 'right', 'success', 'Start recognition process')

          this.getVoiceTextInterval = setInterval(() => {
            this.getVoiceText()
          }, 5000);
        })
        .catch(response => {
          this.status = 'upload';
          this.notifyVue('top', 'right', 'danger', 'Failed to start recognition process')
          console.log('failed');
        })
    },
    getVoiceText() {
      let config = {
        params: {
            job_name: this.job_name
          }
      };
      axios
        .get('/api/aws/text', config)
        .then(response => {
          console.log('success');

          let data = response.data;
          let status = data['status'];
          this.transcript = data['transcript'];

          this.histories[this.object_name]['status'] = status;
          this.histories[this.object_name]['status'] = status;
          this.saveHistories();

          if (status == 'FAILED') {
            console.log('Failed to recognize');
            this.notifyVue('top', 'right', 'danger', 'Failed to recognize')
            this.status = 'upload';
            clearInterval(this.getVoiceTextInterval);
          }
          else if (status == 'COMPLETED') {
            console.log('COMPLETED');
            this.status = 'complete';

            this.histories[this.object_name]['transcript'] = this.transcript;
            this.saveHistories();

            clearInterval(this.getVoiceTextInterval);
            this.notifyVue('top', 'right', 'success', 'Recognition completed')
          }
        })
        .catch(response => {
          console.log('failed');
          clearInterval(this.getVoiceTextInterval);
        })
    },
  }
};
</script>
<style>
</style>